from urllib.parse import quote_plus

from flask import Flask, render_template, request
from database import *

from param_checker import *
from utils import *
from web_utils import *

app = Flask(__name__, static_folder="static", static_url_path="/static")
config = read_config("config.json")
DB = Database(config)


@app.route('/')
def get_requests():
    requests = DB.select_all_requests()
    pretty_req = get_html_requests(requests)
    return render_template("requests.html", table=pretty_req)


@app.route('/request', methods=['GET', 'POST'])
def send_request():
    if request.method == 'GET':
        host = request.args.get('host')
        req = request.args.get('request')
        return render_template("send_request.html", host="" if host is None else host, request="" if req is None else req)

    host = request.form.get('host').strip().replace('\r', '')
    req = request.form.get('request').strip().replace('\r', '')
    secure = True if request.form.get('https') is not None else False
    if not host:  # autocomplete Host
        host_end_idx = host_start_idx = req.lower().find("host:") + len("host:")
        while host_end_idx < len(req) and req[host_end_idx] not in ['\n', '/']:
            host_end_idx += 1
        host = (req[host_start_idx: host_end_idx]).strip()

    reply = ""
    try:
        reply, parser = http_request(req, host, secure, True)
    except:
        pass

    if not reply:
        reply = "<h1>No response</h1>".encode()
    else:
        DB.insert_request(req, host)
        headers_end_idx = reply.find(b'\r\n\r\n')
        reply = b'<div id="headers" class="headers">' + reply[:headers_end_idx].replace(b'\r\n', b'<br>') + b'</div>' + \
                b'<div id="response" class="response">' + reply[headers_end_idx:] + b'</div>'

    file = open("./templates/response.html", "r")
    html = file.read()
    html = html.encode().replace(b"{{ response }}", reply)
    file.close()
    return html


@app.route('/request/<int:id>')
def get_request_by_id(id):
    req = DB.select_request_by_id(id)
    pretty_req = get_html_requests([req])
    return render_template("request.html", table=pretty_req, id=id, host=req[1],
                           request=quote_plus(req[2]))


@app.route('/param-miner/<int:id>')
def check_request_page(id):
    param_name = request.args.get('param')
    change_what = request.args.get('change')

    req = list(DB.select_request_by_id(id))
    pretty_req = get_html_requests([req])
    if not param_name or not change_what:
        return render_template("check_request.html", table=pretty_req)

    change_function = change_param_name if change_what == "name" else change_param_value
    return check_request(req[1], req[2], req[3], param_name, change_function)


def get_html_requests(requests):
    table = """<table>
    <thead>
        <tr>
            <th>id</th>
            <th>host</th>
            <th>request</th>
            <th>Has TLS</th>
        </tr>
    </thead>
    <tbody>
    """
    tbody = ""
    for req in requests:
        row = """
        <tr onclick="window.location.href='/request/%s'" style="cursor: pointer">
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (req[0], req[0], req[1], req[2].replace('\n', '<br>'), req[3])
        tbody += row

    table += tbody + "</tbody></table>"
    return table


@app.route("/repeat/<int:id>")
def repeat_request(id):
    req = list(DB.select_request_by_id(id))

    reply, parser = http_request(req[2], req[1], req[3], True)
    if not reply:
        reply = "No response".encode()
    else:
        headers_end_idx = reply.find(b'\r\n\r\n')
        reply = b"<div class='headers'>" + reply[:headers_end_idx].replace(b"\r\n", b"<br>") + b"</div>" + \
                b"<div id='response' class='response'>" + reply[headers_end_idx:] + b"</div>"

    file = open("./templates/response.html", "r")
    html = file.read()
    html = html.encode().replace(b"{{ response }}", reply)
    file.close()
    return html


@app.route("/clear")
def clear_db():
    DB.clear()

    return "<h1>База данных очищена</h1>" \
           "<button onclick=\"document.location='/'\">На главную</button>"


@app.errorhandler(404)
def show_404(_):
    return "<h1>Страница не найдена</h1>" \
           "<button onclick=\"document.location='/'\">На главную</button>"


if __name__ == '__main__':
    app.run(port=config['web_interface_port'])
