import random

from main_proxy import http_request
from utils import str_between

good_values = [
    "asfdgbgfvasdcxvbb",
    "fgmfyhtyhf",
    "waefqgse",
]


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
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:]


def change_param_name(request, param_name, new_param_name):
    url, url_start_idx, url_end_idx = str_between(request, "GET", "HTTP")
    url = url.strip()
    param_idx = url.find(param_name)
    if param_idx == -1:  # param not in url
        if url.find("?") == -1:  # no query-params
            url += "?"
        else:
            url += "&"
        url += new_param_name + "=" + random.choice(good_values)
    else:  # param in url
        url = url.replace(param_name, new_param_name)
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:]


def check_request(host: str, request: str, secure: bool, param_name: str, check_function) -> str:
    normal_reply = None
    normal_request = None
    bad_params = ""

    for good_param in good_values:
        cur_request = check_function(request, param_name, good_param)
        reply = http_request(cur_request, host, secure)
        if not normal_reply:
            normal_reply = reply
            normal_request = cur_request
        elif reply != normal_reply:
            return "<h1>Не получается начать проверку</h1><br>" \
                   "Ответы должны быть одинаковы, но на запрос:<br>" + normal_request +\
                   "Ответ:<br>" + str(normal_reply) + \
                   "<br><br>А на запрос:<br>" + cur_request + \
                   "Ответ:<br>" + str(reply)

    file = open("param_samples.txt", "r")
    while True:
        param = file.readline()
        if not param:
            break
        param = param.rstrip('\n')

        cur_request = check_function(request, param_name, param)
        reply = http_request(cur_request, host, secure)
        if reply != normal_reply:
            bad_params += param + "<br>"
            print(param, "BAD")
        else:
            print(param, "GOOD")
    file.close()

    if not bad_params:
        return "<h1>Запрос не выглядит уязвимым<h1>"
    return "<h1>Найдены уязвимости с параметрами:</h1><br>" + bad_params


