import flask
from flask import Flask, render_template, request
from database import *

# from scan import scan_request
from main import recv_from_host
from scan import check_request

app = Flask(__name__)
DB = Database()


@app.route('/')
def get_requests():
    requests = DB.select_all_requests()
    pretty_req = get_html_requests(requests)
    return render_template("requests.html", table=pretty_req)


@app.route('/request/<int:id>')
def get_request(id):
    req = DB.select_request_by_id(id)
    pretty_req = get_html_requests([req])
    return render_template("requests.html", table=pretty_req) + \
           "<button onclick=\"document.location='/'\">На главную</button>" + \
           "<button onclick=\"document.location='/repeat/" + str(id) + "'\">Повторить</button>" + \
           "<button onclick=\"document.location='/param-miner/" + str(id) + "'\">Проверить param-miner\'ом</button>"


@app.route('/param-miner/<int:id>')
def scan_request_route(id):
    param_name = request.args.get('param')
    req = DB.select_request_by_id(id)

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
    request = DB.select_request_by_id(id)
    reply = recv_from_host(request[2], request[1], 80)
    return reply


@app.errorhandler(404)
def show_404(_):
    return "<h1>Страница не найдена</h1>" \
           "<button onclick=\"document.location='/'\">На главную</button>"


if __name__ == '__main__':
    app.run(port=8000)
