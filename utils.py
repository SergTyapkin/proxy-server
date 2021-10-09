import json


def str_between(string: (str, bytes), start: (str, bytes), end: (str, bytes), replace_to: (str, bytes) = None):
    end_idx = start_idx = string.find(start) + len(start)
    if isinstance(end, list):
        while string[end_idx] not in end and end_idx < len(string):
            end_idx += 1
    else:
        end_idx = string.find(end)

    if replace_to is not None:
        return string[:start_idx] + replace_to + string[end_idx:]
    else:
        return string[start_idx: end_idx], start_idx, end_idx


def read_config(filepath: str) -> dict:
    try:
        file = open(filepath, "r")
        config = json.load(file)
        file.close()
        config["proxy_host"] = ""
        return config
    except:
        print("Can't open and serialize config.json")
        exit()


def html_prettify(headers: list, body: list, multilines: bool = False, row_onclick=None) -> str:
    if multilines:
        value_foo = lambda val: str(val).replace('\n', '<br>')
    else:
        value_foo = lambda val: str(val)

    thead = "<thead>\n"
    tbody = "<tbody>\n"
    for header in headers:
        thead += "<tr>\n"
        tbody += "<th>" + header + "</th>"
    thead += "</tr>\n"

    for row in body:
        tbody += "<tr" + ((" onclick=" + row_onclick(row[0]) + " style=\"cursor: pointer\"") if row_onclick else "") + ">\n"
        for value in row:
            tbody += "<td>" + value_foo(value) + "</td>"
        tbody += "</tr>\n"
    thead += "</thead>\n"
    tbody += "</tbody>\n"

    return "<table>\n" + thead + tbody + "</table>"

    '''tbody = "<div class=\"grid-rows\">\n"
    trow = "<div class=\"grid-columns\">\n"
    for header in headers:
        trow += "<div>" + header + "</div>\n"
    trow += "</div>\n"
    tbody += trow

    for row in body:
        trow = "<div class=\"grid-columns\"" + ((" onclick=" + row_onclick(row[0]) + " style=\"cursor: pointer\"") if row_onclick else "") + ">\n"
        for value in row:
            trow += "<div>" + value_foo(value) + "</div>"
        trow += "</div>\n"
        tbody += trow

    return tbody + "</div>"'''
