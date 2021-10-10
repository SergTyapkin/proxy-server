import threading
from itertools import islice

from main_proxy import http_request
from utils import str_between, count_lines

good_values = [
    "asfdgbgfvasdcxvbb",
    "fgmfyhtyhf",
    "waefqgse",
]

FILENAME = "small_param_samples.txt"
THREADS = 20


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
        cur_request, url = check_function(request, param_name, good_param)
        response, parser = http_request(cur_request, host, secure)
        splitted_response = response.split(b'\r\n\r\n')
        reply = splitted_response[1] if len(splitted_response) >= 2 else b''
        cur_len = int(parser.get_headers().get('content-length'))
        if not normal_reply:
            normal_reply = reply
            normal_request = cur_request
            normal_len = cur_len
        elif reply != normal_reply or cur_len != normal_len:
            if reply.find(good_param.encode()) != -1:
                return "Скорее всего, запрос уязвим", \
                    [("Не удалось начать проверку, но:", 1),
                     (url + " - Найдено \"" + good_param + "\" в ответе!", 2)]
            return "Не получается начать проверку", \
                   [("Ответы должны быть одинаковы", 1),
                    ("Но на запрос:", 1), (normal_request, 0),
                    ("Ответ: ", 1), (str(normal_reply), 0),
                    ("", 1),
                    ("А на запрос:", 1), (cur_request, 0),
                    ("Ответ: ", 1), (str(reply), 0)]

    log = []
    found_exploits = [False]  # to make mutable
    mutex = threading.Condition()

    def check_values_between(start: int, end: int):
        with open(FILENAME, 'r') as file:
            params = islice(file, start, end)
            for param in params:
                if not param:
                    continue
                param = param.rstrip('\n')

                cur_request, url = check_function(request, param_name, param)

                response, parser = http_request(cur_request, host, secure)
                splitted_response = response.split(b'\r\n\r\n')
                reply = splitted_response[1] if len(splitted_response) >= 2 else b''
                cur_len = int(parser.get_headers().get('content-length'))
                found = False
                if reply != normal_reply:
                    found = True
                    result = [url + " - Отличается ответ", 1]
                elif cur_len != normal_len:
                    found = True
                    result = [url + " - Отличается длина", 1]
                else:
                    result = [url + " - OK", 0]

                if found and (reply.find(param_name.encode()) != -1):
                    result[0] += ". Найдено \"" + param_name + "\" в ответе!"
                    result[1] = 2

                mutex.acquire()
                if found:
                    found_exploits[0] = True
                log.append(result)
                mutex.release()

    lines = count_lines(FILENAME)
    lines_per_thread = lines // THREADS
    cur_line = 0
    threads = []
    for i in range(THREADS):
        if i != THREADS - 1:
            thread = threading.Thread(target=check_values_between, args=(cur_line, cur_line + lines_per_thread))
        else:
            thread = threading.Thread(target=check_values_between, args=(cur_line, lines))
        cur_line += lines_per_thread
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    if not found_exploits[0]:
        return "Уязвимостей не обнаружено", log
    return "Найдены уязвимости!", log
