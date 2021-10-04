from main import recv_from_host, DB


def change_param(req, param_name):
    param_idx = req[1].find(param_name) + len(param_name) + 1
    print(req[0][param_idx:])
    return req


def check_request(req, param_name):
    req = change_param(req, param_name)
    reply_bytes = recv_from_host(request_with_payload, host, 80, 0)

    rep.insert_request(request_with_payload, host, tls)
    reply = reply_bytes.decode()

    return reply.find('root:') >= 0
