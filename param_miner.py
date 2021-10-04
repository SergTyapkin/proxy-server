from main import recv_from_host
from utils import str_between

good_params = [
    "asfdgbgfvasdcxvbb",
]

def change_param(request, param_name, param_value):
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
        url = str_between(url, param_name, ['\n', '&', '?'], param_value)[0]
    return request[:url_start_idx] + " " + url + " " + request[url_end_idx:]


def check_request(req, param_name):
    req = list(req)

    normal_reply = None
    normal_request = None
    bad_params = ""

    for good_param in good_params:
        cur_request = change_param(req[2], param_name, good_param)
        reply = recv_from_host(cur_request, req[1], 80)
        if reply:
            reply = reply[reply.find(b'\r\n\r\n') + len(b'\r\n\r\n'):]
        if not normal_reply:
            normal_reply = reply
            normal_request = cur_request
        elif reply != normal_reply:
            return "<h1>Can't start testing</h1><br>" \
                   "Requests must be good but request:<br>" + normal_request +\
                   "Response:<br>" + str(normal_reply) + \
                   "<br><br>Is not the same as:<br>" + cur_request + \
                   "Response:<br>" + str(reply)

    file = open("param_samples.txt", "r")
    while True:
        param = file.readline()
        if not param:
            break
        param = param.strip()

        cur_request = change_param(req[2], param_name, param)
        reply = recv_from_host(cur_request, req[1], 80)
        reply = reply[reply.find(b'\r\n\r\n') + len(b'\r\n\r\n'):]
        if reply != normal_reply:
            bad_params += param + "<br>"
            print(param, "BAD")
        else:
            print(param, "GOOD")
    file.close()

    if not bad_params:
        return "<h1>Request not seems to be vulnerable<h1>"
    return "<h1>Found some vulnerabilities with params:</h1><br>" + bad_params


