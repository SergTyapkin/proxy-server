import os.path
import subprocess
import time
from _thread import start_new_thread

from utils import *
from web_utils import *
from colorize import *
from database import *

try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser

CERT_DIR = "./certs/"
CERT_KEY = "cert.key"
CA_CERT = "ca.cert"
CA_KEY = "ca.key"

CONNECTION_ESTABILISHED = b'HTTP/1.1 200 Connection Established\r\n\r\n'
RESPONSE_PREVIEW_LEN = 400

# cl_... is client variables
# sv_... is remote web-server variables


def proxy_http(cl_parser, cl_sock, DB: Database, post_data):
    headers = cl_parser.get_headers()
    if len(headers.keys()) < 2:
        cl_sock.close()
        return
    host = headers["host"]

    print(YELLOW + "HTTP:", host, headers, DEFAULT)

    # prepare request to server
    host, method, url, str_headers, cookie = split_request(host, cl_parser)
    sv_request = str_headers + '\n' + post_data

    # get answer from server
    reply, _ = http_request(sv_request, host)

    # re-send answer to client
    cl_sock.sendall(reply)
    cl_sock.close()

    print(CYAN + UNDERLINE + "CLOSED:", host, DEFAULT)

    # insert request into database
    try:
        response = reply.decode()
    except UnicodeDecodeError:
        response = 'Proxy can\'t decode response'
    if post_data == '':
        post_data = None
    if len(response) > RESPONSE_PREVIEW_LEN:
        response = response[:RESPONSE_PREVIEW_LEN] + '...'
    DB.execute(DB.INSERT_REQUEST, [host, method, url, str_headers, cookie, post_data, response])


def proxy_https(cl_parser, cl_sock, DB: Database):
    host = cl_parser.get_headers()['host']
    host = host[:host.find(':')].rstrip('/')

    print(GREEN + "HTTPS:", host, cl_parser.get_headers(), DEFAULT)

    # generate cert
    cert_full_path = generate_cert(host)

    # Send established message
    cl_sock.sendall(CONNECTION_ESTABILISHED)
    cl_sock_secure = ssl.wrap_socket(cl_sock, keyfile=CERT_KEY, certfile=cert_full_path, server_side=True)
    cl_sock_secure.do_handshake()

    # get http request from https connection
    cl_http_parser = HttpParser()
    cl_http_request = receive_data(cl_sock_secure, cl_http_parser)

    # get reply from server
    sv_reply, _ = http_request(cl_http_request, host, secure=True)

    # re-send answer to client
    cl_sock_secure.sendall(sv_reply)
    cl_sock_secure.close()

    print(CYAN + UNDERLINE + "CLOSED:", host, DEFAULT)

    # insert request into database
    host, method, url, str_headers, cookie = split_request(host, cl_http_parser)
    try:
        response = sv_reply.decode()
    except UnicodeDecodeError:
        response = 'Proxy can\'t decode response'
    post_data = get_post_data(cl_http_request).strip('\n ')
    if post_data == '':
        post_data = None
    if len(response) > RESPONSE_PREVIEW_LEN:
        response = response[:RESPONSE_PREVIEW_LEN] + '...'
    DB.execute(DB.INSERT_REQUEST, [host, method, url, str_headers, cookie, post_data, response, True])


def generate_cert(host: str) -> str:
    cert_name = host + ".crt"
    cert_full_path = CERT_DIR + cert_name
    if os.path.exists(cert_full_path):
        return cert_full_path

    conf_full_path = generate_cert_config(host)

    uid = int(time.time() * 100000)
    subprocess.call(
        f'openssl req -new -key cert.key -subj "/CN={host}" -sha256 | ' +
        f'openssl x509 -req -days 3650 -CA ca.crt -CAkey ca.key -set_serial {uid} -out {cert_full_path} ' +
                     f'-extensions v3_ca -extfile {conf_full_path}',
        shell=True)

    return cert_full_path


def generate_cert_config(host: str) -> str:
    conf_path = CERT_DIR + host + ".cnf"
    if os.path.exists(conf_path):
        return conf_path

    with open(conf_path, 'w') as fp:
        fp.write(f"""[ v3_ca ]
        subjectAltName = DNS:{host}
        """)
    return conf_path


if __name__ == "__main__":
    config = read_config("config.json")
    DB = Database(config)

    while True:
        cl_sock = open_listen_socket(config["proxy_host"], int(config["proxy_port"]))

        try:
            parser = HttpParser()

            cl_sock, _ = cl_sock.accept()
            data = receive_data(cl_sock, parser)

            if parser.get_method() == "CONNECT":
                start_new_thread(proxy_https, (parser, cl_sock, DB))
            else:
                start_new_thread(proxy_http, (parser, cl_sock, DB, get_post_data(data)))

        except KeyboardInterrupt:
            exit()
        except Exception as e:
            cl_sock.close()
            print(e.args)
            print(RED + UNDERLINE + "CLOSED" + DEFAULT)
