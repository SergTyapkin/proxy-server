import threading
from itertools import islice

from main_proxy import http_request
from utils import str_between, count_lines

good_values = [
    "asfdgbgfvasdcxvbb",
    "fgmfyhtyhf",
    "waefqgse",
]

FILENAME = "param_samples.txt"
THREADS = 20


def change_param_value(request, param_name, param_value):
    url, url_start_idx, url_end_idx = str_between(request, "GET", "HTTP")
    url = url.strip()
    if url.find('?') == -1:  # no query-params
        url += "?" + param_name + "=" + param_value
    else:
        if url.find(param_name) == -1:  # param not in url
            url += "&" + param_name + "=" + param_value
        else:  # param in url
            url, query = url.split('?')
            query = str_between(query, param_name + '=', ['&', '\n', ' '], replace_to=param_value)
            url += "?" + query
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:], url


def change_param_name(request, param_name, new_param_name):
    url, url_start_idx, url_end_idx = str_between(request, "GET", "HTTP")
    url = url.strip()
    if url.find('?') == -1:  # no query-params
        url += "?" + new_param_name + "=" + param_name
    else:
        url, query = url.split('?')
        if query.find(new_param_name) == -1:  # param not in query
            query += "&" + new_param_name + "=" + param_name
        else:  # param in url
            query = str_between(query, new_param_name + '=', ['&', '\n', ' '], replace_to=param_name)
        url += "?" + query
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:], url


def check_request(host: str, request: str, secure: bool, param_name: str, check_function, result, params, isFinished):
    normal_reply = None
    normal_request = None
    normal_len = None

    for good_param in good_values:
        cur_request, url = check_function(request, param_name, good_param)
        response, parser = http_request(cur_request, host, secure)
        splitted_response = response.split(b'\r\n\r\n')
        reply = splitted_response[1] if len(splitted_response) >= 2 else b''
        try:
            cur_len = int(parser.get_headers().get('content-length'))
        except TypeError:
            cur_len = 0
        if not normal_reply:
            normal_reply = reply
            normal_request = cur_request
            normal_len = cur_len
        elif reply != normal_reply or cur_len != normal_len:
            if reply.find(good_param.encode()) != -1:
                result[0] = "Скорее всего, запрос уязвим"
                params += [("Не удалось начать проверку, но:", 1),
                           (url + " - Найдено \"" + good_param + "\" в ответе!", 2)]
                return
            result[0] = "Не получается начать проверку"
            params += [("Ответы должны быть одинаковы", 1),
                       ("Но на запрос:", 1), (normal_request, 0),
                       ("Ответ: ", 1), (str(normal_reply), 0),
                       ("", 1),
                       ("А на запрос:", 1), (cur_request, 0),
                       ("Ответ: ", 1), (str(reply), 0)]
            return

    found_exploits = [False]  # to make mutable
    mutex = threading.Condition()

    def check_values_between(start: int, end: int):
        with open(FILENAME, 'r') as file:
            cur_params = islice(file, start, end)
            for param in cur_params:
                if not param:
                    continue
                param = param.rstrip('\n')

                cur_request, url = check_function(request, param_name, param)

                response, parser = http_request(cur_request, host, secure)
                splitted_response = response.split(b'\r\n\r\n')
                reply = splitted_response[1] if len(splitted_response) >= 2 else b''
                try:
                    cur_len = int(parser.get_headers().get('content-length'))
                except TypeError:
                    cur_len = 0
                found = False
                if reply != normal_reply:
                    found = True
                    cur_result = [url + " - Отличается ответ", 1]
                elif cur_len != normal_len:
                    found = True
                    cur_result = [url + " - Отличается длина", 1]
                else:
                    cur_result = [url + " - OK", 0]

                if found and (reply.find(param_name.encode()) != -1):
                    cur_result[0] += ". Найдено \"" + param_name + "\" в ответе!"
                    cur_result[1] = 2

                mutex.acquire()
                if found:
                    found_exploits[0] = True
                    result[0] = "Найдены уязвимости!"
                params.append(cur_result)
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

    def daemon():
        for cur_thread in threads:
            cur_thread.join()

        if not found_exploits[0]:
            result[0] = "Уязвимостей не обнаружено"

        isFinished[0] = True
        return

    threading.Thread(target=daemon).start()
    return
