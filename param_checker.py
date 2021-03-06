import gzip
import threading
from itertools import islice

from main_proxy import http_request
from utils import str_between, count_lines, read_config

good_values = [
    "asfdgbgfvasdcxvbb",
    "fgmfyhtyhf",
    "waefqgse",
]

FILENAME = "param_samples.txt"
THREADS = read_config('config.json')['threads_for_check']


def change_param_value(request, param_name, param_value):
    url, url_start_idx, url_end_idx = str_between(request, "GET", "HTTP")
    url = url.strip()
    if url.find('?') == -1:  # no query-params
        url += "?" + param_name + "=" + param_value
    else:
        url, query = url.split('?')
        queryParams = query.split('&')
        found = False
        query = ''
        for queryParam in queryParams:
            splitted = queryParam.split('=')
            name = splitted[0]
            value = splitted[1]
            if name == param_name:
                value = param_value
                found = True
            query += name + '=' + value + '&'
        query = query[:-1]

        if not found:  # param not in query
            query += "&" + param_name + "=" + param_value
        url += "?" + query
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:], url


def change_param_name(request, param_name, new_param_name):
    return change_param_value(request, new_param_name, param_name)


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
                result[0] = "???????????? ??????????, ???????????? ????????????"
                params += [("???? ?????????????? ???????????? ????????????????, ????:", 1),
                           (url + " - ?????????????? \"" + good_param + "\" ?? ????????????!", 2)]
                isFinished[0] = True
                return
            result[0] = "???? ???????????????????? ???????????? ????????????????"
            params += [("???????????? ???????????? ???????? ??????????????????", 1),
                       ("???? ???? ????????????:", 1), (normal_request, 0),
                       ("??????????: ", 1), (str(normal_reply), 0),
                       ("", 1),
                       ("?? ???? ????????????:", 1), (cur_request, 0),
                       ("??????????: ", 1), (str(reply), 0)]
            isFinished[0] = True
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
                    cur_result = [url + " - ???????????????????? ??????????", 1]
                elif cur_len != normal_len:
                    found = True
                    cur_result = [url + " - ???????????????????? ??????????", 1]
                else:
                    cur_result = [url + " - OK", 0]

                encodings = parser.get_headers().get('CONTENT-ENCODING')
                if encodings and (encodings.find('gzip') != -1):
                    try:
                        reply = gzip.decompress(reply)
                    except:
                        pass

                if found and (reply.find(param_name.encode()) != -1):
                    cur_result[0] += ". ?????????????? \"" + param_name + "\" ?? ????????????!"
                    cur_result[1] = 2

                mutex.acquire()
                if found:
                    found_exploits[0] = True
                    result[0] = "?????????????? ????????????????????!"
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
            result[0] = "?????????????????????? ???? ????????????????????"

        isFinished[0] = True
        return

    threading.Thread(target=daemon).start()
    return
