from string import Template

from flask import Flask, render_template, request
from database import *

# from scan import check_request
from main import recv_from_host
from param_miner import check_request

app = Flask(__name__)
DB = Database()


@app.route('/')
def get_requests():
    requests = DB.select_all_requests()
    pretty_req = get_html_requests(requests)
    return render_template("requests.html", table=pretty_req)


@app.route('/request', methods=['GET', 'POST'])
def send_request():
    if request.method == 'GET':
        return render_template("request.html")

    req = [request.form.get('host'), request.form.get('request')]
    if not req[0]:  # autocomplete Host
        host_end_idx = host_start_idx = req[1].find("Host:") + len("Host:")

        while req[1][host_end_idx] not in ['\n', '/'] and host_end_idx < len(req[1]):
            host_end_idx += 1
        req[0] = (req[1][host_start_idx: host_end_idx]).strip()

    # url_start_idx = req[1].find("GET") + len("GET")
    # url_end_idx = req[1].find("HTTP")
    # url = (req[1][url_start_idx: url_end_idx]).strip()
    # req[1] = req[1][:url_start_idx] + url + req[1][url_end_idx:]

    req[1] += '\r\n\r\n'

    reply = recv_from_host(req[1], req[0], 80)
    if not reply:
        return "<button onclick=\"history.go(-1)\">Назад</button>" + \
               "<h1>No response</h1>"
    return "<button onclick=\"history.go(-1)\">Назад</button><br>".encode() + reply


@app.route('/request/<int:id>')
def get_request_by_id(id):
    req = DB.select_request_by_id(id)
    pretty_req = get_html_requests([req])
    return render_template("requests.html", table=pretty_req) + \
           "<button onclick=\"document.location='/'\">На главную</button>" + \
           "<button onclick=\"document.location='/repeat/" + str(id) + "'\">Повторить</button>" + \
           "<button onclick=\"document.location='/param-miner/" + str(id) + "'\">Проверить param-miner\'ом</button>"


@app.route('/param-miner/<int:id>')
def check_request_page(id):
    param_name = request.args.get('param')
    if not param_name:
        return render_template("check_request.html")

    req = list(DB.select_request_by_id(id))

    return check_request(req, param_name)


def get_html_requests(requests):
    table = """<table>
    <thead>
        <tr>
            <th>id</th>
            <th>host</th>
            <th>request</th>
        </tr>
    </thead>
    <tbody>
    """
    for req in requests:
        table += """
        <tr onclick="window.location.href='/request/%s'" style="cursor: pointer">
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (req[0], req[0], req[1], req[2].replace('\n', '<br>'))

    table += "</tbody></table>"
    return table


@app.route("/repeat/<int:id>")
def repeat_request(id):
    req = list(DB.select_request_by_id(id))

    # url_start_idx = req[2].find("GET") + len("GET")
    # url_end_idx = req[2].find("HTTP")
    # url = (req[2][url_start_idx: url_end_idx]).strip()
    # req[2] = req[2][:url_start_idx] + url + req[2][url_end_idx:]

    reply = recv_from_host(req[2], req[1], 80)
    if not reply:
        return "No response"
    return "<button onclick=\"history.go(-1)\">К запросу</button><br>".encode() + reply


@app.errorhandler(404)
def show_404(_):
    return "<h1>Страница не найдена</h1>" \
           "<button onclick=\"document.location='/'\">На главную</button>"


if __name__ == '__main__':
    app.run(port=8000)
