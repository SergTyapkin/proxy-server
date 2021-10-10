import random

from main_proxy import http_request
from utils import str_between, count_lines

good_values = [
    "asfdgbgfvasdcxvbb",
    "fgmfyhtyhf",
    "waefqgse",
]

FILENAME = "small_param_samples.txt"


def change_param_value(request, param_name, param_value):
    url, url_start_idx, url_end_idx = str_between(request, "GET", "HTTP")
    url = url.strip()
    param_idx = url.find(param_name)
    if param_idx == -1:  # param not in url
        if url.find("?") == -1:  # no query-params
            url += "?"
        else:
            url += "&"
        url += param_name + "=" + param_value
    else:  # param in url
        url, _, _ = str_between(url, param_name, ['\n', '&', '?'], param_value)
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:], url


def change_param_name(request, param_name, new_param_name):
    url, url_start_idx, url_end_idx = str_between(request, "GET", "HTTP")
    url = url.strip()
    param_idx = url.find(new_param_name)
    if param_idx == -1:  # param not in url
        if url.find("?") == -1:  # no query-params
            url += "?"
        else:
            url += "&"
        url += new_param_name + "=" + param_name
    else:  # param in url
        url = str_between(url, new_param_name + '=', ['&', '\n', ' '], replace_to=param_name)
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:], url


def check_request(host: str, request: str, secure: bool, param_name: str, check_function) -> (str, list or None):
    normal_reply = None
    normal_request = None
    normal_len = None

    for good_param in good_values:
        cur_request, _ = check_function(request, param_name, good_param)
        response, parser = http_request(cur_request, host, secure)
        splitted_response = response.split(b'\r\n\r\n')
        reply = splitted_response[1] if len(splitted_response) >= 2 else ''
        cur_len = int(parser.get_headers().get('content-length'))
        if not normal_reply:
            normal_reply = reply
            normal_request = cur_request
            normal_len = cur_len
        elif reply != normal_reply or cur_len != normal_len:
            return "<h1>Не получается начать проверку</h1><br>" \
                   "Ответы должны быть одинаковы, но на запрос:<br>" + normal_request +\
                   "<br>Ответ:<br>" + str(normal_reply) + \
                   "<br><br>А на запрос:<br>" + cur_request + \
                   "<br>Ответ:<br>" + str(reply), None

    log = []
    found_exploits = False
    with open(FILENAME, "r") as file:
        while True:
            param = file.readline()
            if not param:
                break
            param = param.rstrip('\n')

            cur_request, url = check_function(request, param_name, param)
            print(count_lines(FILENAME))
            response, parser = http_request(cur_request, host, secure)
            splitted_response = response.split(b'\r\n\r\n')
            reply = splitted_response[1] if len(splitted_response) >= 2 else ''
            cur_len = int(parser.get_headers().get('content-length'))
            if reply != normal_reply:
                found_exploits = True
                log.append(url + " - Different content")
                print(param, "BAD content")
            elif cur_len != normal_len:
                found_exploits = True
                log.append(url + " - Different length")
                print(param, "BAD length")
            else:
                log.append(url + " - OK")
                print(param, "GOOD")

    if not found_exploits:
        return "Уязвимостей не обнаружено", log
    return "Найдены уязвимости!", log


