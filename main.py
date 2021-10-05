from _thread import start_new_thread
from database import *
import socket

from utils import open_socket, read_config

try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser


BUF_SIZE = 4096


def receive_data(sock: socket, parser: HttpParser) -> bytes:
    data = b""
    while not parser.is_message_complete():
        chunk = sock.recv(BUF_SIZE)
        if not chunk:
            break

        parser.execute(chunk, len(chunk))
        data += chunk
    return data


def proxy_http(cl_request, cl_parser, cl_sock, DB):
    # prepare request to server
    headers = cl_parser.get_headers()
    cleanup_headers(headers)
    wsgi = cl_parser.get_wsgi_environ()
    sv_request = wsgi['REQUEST_METHOD'] + " " + wsgi['PATH_INFO'] + " " + wsgi['SERVER_PROTOCOL'] + "\n"
    sv_request += headers_to_string(headers) + "\n"
    # print(parser.get_path())
    # print(parser.get_fragment())
    # print(parser.get_headers())
    # print(parser.get_url())
    # print(parser.get_method())
    # print(parser.get_query_string())
    # print(parser.get_status_code())
    # print(parser.get_version())
    # print(parser.get_wsgi_environ())
    # print("++++++")
    # print(cl_request.decode())
    print("\nSEND REQUEST:", sv_request)
    # get answer from server
    reply, sv_parser = http_request(sv_request, headers["host"], 80)
    # re-send answer to client
    cl_sock.sendall(reply)
    cl_sock.close()

    DB.insert_request(sv_request, headers["host"])


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


def http_request(request: str, host: str, port: int):
    sv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sv_sock.connect((host, port))
    except:
        sv_sock.close()
        raise ValueError("Can't connect to host:" + host + "port:" + str(port))
    sv_sock.sendall(request.encode())

    parser = HttpParser()
    reply = receive_data(sv_sock, parser)
    sv_sock.close()

    print("\nGET ANSWER:")
    print(parser.get_path())
    print(parser.get_fragment())
    print(parser.get_headers())
    print(parser.get_url())
    print(parser.get_method())
    print(parser.get_query_string())
    print(parser.get_status_code())
    print(parser.get_version())
    print(parser.get_wsgi_environ())
    print(parser.is_message_complete())
    print(parser.is_headers_complete())
    print(parser.is_chunked())
    print("++++++")
    return reply, parser


# cl_... is client variables
# sv_... is remote web-server variables
if __name__ == "__main__":
    config = read_config("config.json")
    DB = Database(config)

    while True:
        cl_sock = open_socket(config["proxy_host"], int(config["proxy_port"]))

        try:
            parser = HttpParser()

            cl_sock, cl_address = cl_sock.accept()
            data = receive_data(cl_sock, parser)

            if parser.get_method() == "CONNECT":
                # print("HTTPS request detected")
                cl_sock.close()
            else:
                print("HTTP request detected")
                start_new_thread(proxy_http, (data, parser, cl_sock, DB))

        except KeyboardInterrupt:
            cl_sock.close()
            exit()
        # except Exception as e:
        #     cl_sock.close()
        #     print(e.args)
