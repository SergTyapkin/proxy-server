from urllib.parse import quote_plus

from flask import Flask, render_template, request, Markup
from database import Database

from utils import *
from web_utils import *

from blueprints.options.routes import app as options_app
from blueprints.param_miner.routes import app as param_miner_app

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.register_blueprint(options_app, url_prefix='/options')
app.register_blueprint(param_miner_app, url_prefix='/param-miner')
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


@app.route('/')
def get_requests():
    req, table_headers = DB.execute_return(DB.SELECT_ALL_REQUESTS)
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
    req, table_headers = DB.execute_return_one(DB.SELECT_REQUEST_BY_ID, [id])
    req[7] = Markup.escape(req[7])  # Escape tags in response
    pretty_req = html_prettify(table_headers, [req], True)
    return render_template("request.html", table=pretty_req, id=id, host=req[1],
                           request=quote_plus(compress_to_request(req)), protocol='https' if req[8] else 'http')


@app.route("/repeat/<int:id>")
def repeat_request(id):
    req, _ = DB.execute_return_one(DB.SELECT_REQUEST_BY_ID, [id])
    req, _ = DB.execute_return_one(DB.SELECT_REQUEST_BY_ID, [id])

    headers, response = decode_http_request(compress_to_request(req), req[1], req[8])
    return render_template("response.html", headers=headers, response=response)


'''
@app.errorhandler(404)
def show_404(_):
    return "<h1>Страница не найдена</h1>" \
           "<button onclick=\"document.location='/'\">На главную</button>"
'''

if __name__ == '__main__':
    app.run(port=config['web_interface_port'])
