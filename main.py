import os.path
import subprocess
import time
from _thread import start_new_thread

import socket
import ssl

from utils import *
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
CERT_COMMANDS_DIR = "/certs"
BUF_SIZE = 4096
CONNECTION_ESTABILISHED = b'HTTP/1.1 200 Connection Established\r\n\r\n'


# cl_... is client variables
# sv_... is remote web-server variables


def receive_data(sock: socket, parser: HttpParser) -> bytes:
    data = b""
    while not parser.is_message_complete():  # and data[-len(b'\r\n\r\n'):] != b'\r\n\r\n':
        cyan()
        chunk = sock.recv(BUF_SIZE)
        if not chunk:
            break

        parser.execute(chunk, len(chunk))
        data += chunk
        parser.is_message_complete()
        parser.is_headers_complete()
    return data


def proxy_http(cl_parser, cl_sock, DB):
    headers = cl_parser.get_headers()
    if len(headers.keys()) < 2:
        cl_sock.close()
        return
    host = headers["host"]

    yellow()
    print("HTTP:", host, headers)
    default()

    # prepare request to server
    cleanup_headers(headers)
    wsgi = cl_parser.get_wsgi_environ()
    sv_request = wsgi['REQUEST_METHOD'] + " " + wsgi['PATH_INFO'] + " " + wsgi['SERVER_PROTOCOL'] + "\n"
    sv_request += headers_to_string(headers) + "\n"

    # get answer from server
    reply, sv_parser = http_request(sv_request, host)

    # re-send answer to client
    cl_sock.sendall(reply)
    cl_sock.close()

    cyan()
    underline()
    print("CLOSED:", host)
    default()

    # insert request into database
    DB.insert_request(sv_request, host)


def headers_to_string(headers: dict):
    sv_request = ""
    for header, value in headers.items():
        sv_request += header + ": " + value + "\n"
    return sv_request


def cleanup_headers(headers: dict):
    for header, value in headers.items():
        if header == "PROXY-CONNECTION":
            headers.pop(header)
            headers["CONNECTION"] = value
        elif header == "ACCEPT-ENCODING":
            headers[header] = value.replace('gzip', 'no_gzip_please')


def http_request(request: (str, bytes), host: str, secure: bool = False):
    port = 443 if secure else 80

    sv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sv_sock.connect((host, port))

    if secure:
        sv_sock = ssl.create_default_context().wrap_socket(sv_sock, server_hostname=host)

    if isinstance(request, bytes):
        sv_sock.sendall(request)
    else:
        sv_sock.sendall(request.encode())

    sv_parser = HttpParser()
    sv_reply = receive_data(sv_sock, sv_parser)
    sv_sock.close()

    return sv_reply, sv_parser


# --------------------------- HTTPS ------------------------------

def proxy_https(cl_parser, cl_sock, DB):
    host = cl_parser.get_headers()['host']
    host = host[:host.find(':')].rstrip('/')

    green()
    print("HTTPS:", host, cl_parser.get_headers())
    default()

    # generate cert
    cert_full_path = generate_cert(host)

    # Send established message
    cl_sock.sendall(CONNECTION_ESTABILISHED)
    cl_sock_secure = ssl.wrap_socket(cl_sock, keyfile=CERT_KEY, certfile=cert_full_path, server_side=True)
    cl_sock_secure.do_handshake()

    # get http request from https connection
    sv_parser = HttpParser()
    sv_request = receive_data(cl_sock_secure, sv_parser)

    # print("\nGET ANSWER:")
    # print(sv_parser.get_path())
    # print(sv_parser.get_fragment())
    # print(sv_parser.get_headers())
    # print(sv_parser.get_url())
    # print(sv_parser.get_method())
    # print(sv_parser.get_query_string())
    # print(sv_parser.get_status_code())
    # print(sv_parser.get_version())
    # print(sv_parser.get_wsgi_environ())
    # print(sv_parser.is_message_complete())
    # print(sv_parser.is_headers_complete())
    # print(sv_parser.is_chunked())
    # print("++++++")

    # get reply from server
    sv_reply, sv_parser = http_request(sv_request, host, True)

    # re-send answer to client
    cl_sock_secure.sendall(sv_reply)
    cl_sock_secure.close()

    cyan()
    underline()
    print("CLOSED:", host)
    default()

    DB.insert_request(headers_to_string(cl_parser.get_headers()), host, True)


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
            red()
            underline()
            print("CLOSED")
            default()
