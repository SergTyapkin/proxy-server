from urllib.parse import quote_plus

from flask import Flask, render_template, request, Markup, jsonify
from database import *

from param_checker import *
from utils import *
from web_utils import *

app = Flask(__name__, static_folder="static", static_url_path="/static")
config = read_config("config.json")
DB = Database(config)


def decode_http_request(req, host, secure):
    try:
        reply, _ = http_request(req, host, secure, gzip_decode=True)
    except:
        reply = None

    headers = ["Nothing received"]
    response = ["No response"]
    if reply:
        headers_end_idx = reply.find(b'\r\n\r\n')
        response_start_idx = headers_end_idx + len(b'\r\n\r\n')
        try:
            headers = reply[:headers_end_idx].decode()
            headers = headers.split('\n')
        except UnicodeDecodeError:
            headers = ["Не удалось раскодировать заголовки"]

        try:
            response = reply[response_start_idx:].decode()
            response = response.replace('\r', '').strip('\n').split('\n')
        except UnicodeDecodeError:
            response = ["Не удалось раскодировать тело ответа:", reply[response_start_idx:]]
    return headers, response


def compress_to_request(req: list) -> str:
    req_body = req[4]  # headers
    if req[5]:  # cookie
        req_body += "COOKIE: " + req[5].replace('\n', ' ') + '\n'
    if req[6]:  # post_data
        req_body += '\n' + req[6]
    return req_body


@app.route('/')
def get_requests():
    req, table_headers = DB.select_all_requests()
    pretty_req = html_prettify(table_headers, req, True, lambda idx: f"window.location.href='/request/{idx}'")
    return render_template("requests.html", table=pretty_req)


@app.route('/request', methods=['GET', 'POST'])
def send_request():
    if request.method == 'GET':
        host = request.args.get('host')
        req = request.args.get('request')
        secure = True if request.args.get('protocol') == 'https' else False
        return render_template("send_request.html", host="" if host is None else host,
                               request="" if req is None else req, secure=secure)

    host = request.form.get('host').strip().replace('\r', '')
    req = request.form.get('request').strip().replace('\r', '')
    secure = True if request.form.get('https') == 'yes' else False
    if not host:  # autocomplete Host
        host_end_idx = host_start_idx = req.lower().find("host:") + len("host:")
        while host_end_idx < len(req) and req[host_end_idx] not in ['\n', '/']:
            host_end_idx += 1
        host = (req[host_start_idx: host_end_idx]).strip()

    headers, response = decode_http_request(req, host, secure)

    return render_template("response.html", headers=headers, response=response)


@app.route('/request/<int:id>')
def get_request_by_id(id):
    req, table_headers = DB.select_request_by_id(id)
    req[7] = Markup.escape(req[7])  # Escape tags in response
    pretty_req = html_prettify(table_headers, [req], True)
    return render_template("request.html", table=pretty_req, id=id, host=req[1],
                           request=quote_plus(compress_to_request(req)), protocol='https' if req[8] else 'http')


_checks = []
@app.route('/param-miner/<int:id>', methods=['GET', 'POST'])
def check_request_by_id(id):
    param_name = request.args.get('param')
    change_what = request.args.get('change')

    req, table_headers = DB.select_request_by_id(id)
    pretty_req = html_prettify(table_headers, [req], True, lambda idx: f"window.location.href='/request/{idx}'")
    if not param_name or not change_what:
        return render_template("check_request.html", table=pretty_req, id=id)

    max_len = count_lines("param_samples.txt")

    check = [id, param_name, change_what, ["Проверка еще идет"], [], [False]]
    found_idx = None
    found = False
    for i in range(len(_checks)):
        cur_check = _checks[i]
        if id == cur_check[0] and param_name == cur_check[1] and change_what == cur_check[2]:
            found_idx = i
            check = cur_check
            found = True
            break
    if found:
        response = jsonify(
            result=check[3][0],
            params=check[4]
        )
        if check[5][0]:  # if finished
            _checks.pop(found_idx)
            response.status_code = 400
        if request.method == 'POST':
            return response
    else:
        _checks.append(check)

    if not found:
        change_function = change_param_name if change_what == "name" else change_param_value
        check_request(req[1], compress_to_request(req), req[8], param_name, change_function, check[3], check[4], check[5])
    return render_template("check_result.html", result=check[3][0], params=check[4], id=id, host=req[1],
                           port=config['web_interface_port'], count=len(check[4]), max_count=max_len)


@app.route("/repeat/<int:id>")
def repeat_request(id):
    req, _ = DB.select_request_by_id(id)
    req, _ = DB.select_request_by_id(id)

    headers, response = decode_http_request(compress_to_request(req), req[1], req[8])
    return render_template("response.html", headers=headers, response=response)


@app.route("/options")
def options():
    return render_template("options.html")


@app.route("/clear_db")
def clear_db():
    DB.clear()
    return render_template("response.html", headers=["База данных успешно очищена"], response=["А вот так вот просто, да"])


@app.route("/reset_db")
def reset_db():
    DB.drop()
    DB.init()
    return render_template("response.html", headers=["База данных успешно пересоздана"], response=["А вот теперь индексы с 1 начнутся"])


'''
@app.errorhandler(404)
def show_404(_):
    return "<h1>Страница не найдена</h1>" \
           "<button onclick=\"document.location='/'\">На главную</button>"
'''


if __name__ == '__main__':
    app.run(port=config['web_interface_port'])
