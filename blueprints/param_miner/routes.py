from flask import Blueprint, render_template, jsonify, request

from param_checker import *
from utils import html_prettify, read_config, compress_to_request
from database import Database

app = Blueprint('param-miner', __name__, template_folder="templates")
config = read_config("config.json")
DB = Database(config)

_checks = []


@app.route('/<int:id>', methods=['GET', 'POST'])
def check_request_by_id(id):
    param_name = request.args.get('param')
    change_what = request.args.get('change')

    req, table_headers = DB.execute_return_one(DB.SELECT_REQUEST_BY_ID, [id])
    pretty_req = html_prettify(table_headers, [req], True)
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
        check_request(req[1], compress_to_request(req), req[8], param_name, change_function, check[3], check[4],
                      check[5])
    return render_template("check_result.html", result=check[3][0], params=check[4], id=id, host=req[1],
                           port=config['web_interface_port'], count=len(check[4]), max_count=max_len)
