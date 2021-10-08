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


# cl_... is client variables
# sv_... is remote web-server variables


def proxy_http(cl_parser, cl_sock, DB):
    headers = cl_parser.get_headers()
    if len(headers.keys()) < 2:
        cl_sock.close()
        return
    host = headers["host"]

    print(YELLOW + "HTTP:", host, headers, DEFAULT)

    # prepare request to server
    cleanup_headers(headers)
    wsgi = cl_parser.get_wsgi_environ()
    sv_request = wsgi['REQUEST_METHOD'] + " " + wsgi['PATH_INFO'] + " " + wsgi['SERVER_PROTOCOL'] + "\n"
    sv_request += headers_to_string(headers)

    # get answer from server
    reply, sv_parser = http_request(sv_request, host)

    # re-send answer to client
    cl_sock.sendall(reply)
    cl_sock.close()

    print(CYAN + UNDERLINE + "CLOSED:", host, DEFAULT)

    # insert request into database
    sv_request.replace('\r', '')
    DB.insert_request(sv_request, host)


def cleanup_headers(headers: dict):
    for header, value in headers.items():
        if header == "PROXY-CONNECTION":
            headers.pop(header)
            headers["CONNECTION"] = value
        elif header == "ACCEPT-ENCODING":
            headers[header] = value.replace('gzip', 'no_gzip_please')


# --------------------------- HTTPS ------------------------------

def proxy_https(cl_parser, cl_sock, DB):
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
    sv_reply, sv_parser = http_request(cl_http_request, host, True)

    # re-send answer to client
    cl_sock_secure.sendall(sv_reply)
    cl_sock_secure.close()

    print(CYAN + UNDERLINE + "CLOSED:", host, DEFAULT)

    # prepare request to save in database
    headers = cl_http_parser.get_headers()
    cleanup_headers(headers)
    wsgi = cl_http_parser.get_wsgi_environ()
    request_to_save = wsgi['REQUEST_METHOD'] + " " + wsgi['PATH_INFO'] + " " + wsgi['SERVER_PROTOCOL'] + "\n"
    request_to_save += headers_to_string(headers | cl_http_parser.get_headers())
    request_to_save.replace('\r', '')
    DB.insert_request(request_to_save, host, True)


def generate_cert(host: str) -> str:
    cert_name = host + ".crt"
    cert_full_path = CERT_DIR + cert_name
    if os.path.exists(cert_full_path):
        return cert_full_path

    uid = int(time.time() * 100000)
    subprocess.call(
        'openssl req -new -key cert.key -subj "/CN=%s" -sha256 | ' % (host) +
        'openssl x509 -req -days 3650 -CA ca.crt -CAkey ca.key -set_serial %s -out %s' % (
            uid, cert_full_path), shell=True)

    return cert_full_path


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
                start_new_thread(proxy_http, (parser, cl_sock, DB))

        except KeyboardInterrupt:
            cl_sock.close()
            exit()
        except Exception as e:
            cl_sock.close()
            print(e.args)
            print(RED + UNDERLINE + "CLOSED" + DEFAULT)
