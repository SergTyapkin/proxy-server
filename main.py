from _thread import start_new_thread
from database import *
import socket
try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser

HOST = ''
PORT = 8080
BUF_SIZE = 4096

cert_dir = "certs"
cert_key = "cert.key"
ca_cert = "ca.crt"
ca_key = "ca.key"


def receive_data_from_socket(sock):
    parser = HttpParser()
    resp = b''
    is_headers_end = False
    headers = b''
    while not parser.is_message_complete():
        data = sock.recv(BUF_SIZE)
        if not data:
            break

        parser.execute(data, len(data))

        if not is_headers_end:
            if data.find(b"charset=UTF-8") == -1:
                headers += data
            else:
                split_idx = data.find(b"charset=UTF-8") + len(b"charset=UTF-8")
                headers += data[:split_idx]
                resp += data[split_idx:]
                is_headers_end = True
        else:
            resp += data
    print(headers)
    print(resp)
    return resp, parser


def cleanup_http_request(parser, data):
    data_array = data.decode("utf-8").split("\n")
    print(data_array)
    url = ""
    if parser.is_headers_complete():
        url = parser.get_url()

    if len(data_array) < 2:
        return None, None
    data_array[0] = data_array[0].replace(url, parser.get_path())

    host = parser.get_headers()['host']

    request_to_host = ""
    for line in data_array:
        if line.find("Proxy-Connection") != -1:
            request_to_host += line + "\n"

    return request_to_host, host


def http_request(request, host, port):
    req_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    req_socket.connect((host.strip(), port))
    req_socket.sendall(request.encode("utf-8"))
    return req_socket


def proxy_http(data, parser, sock, DB):
    request, host = cleanup_http_request(parser, data)
    reply = recv_from_host(request, host, 80)
    sock.sendall(reply)
    sock.close()
    DB.insert_request(request, host, 0)
    return reply


def recv_from_host(request, host, port):
    req_socket = http_request(request, host, port)
    reply, _ = receive_data_from_socket(req_socket)
    req_socket.close()
    return reply


DB = Database()

if __name__ == '__main__':
    while True:
        # Create a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Re-use the socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind the socket to a public host, and a port
        sock.bind((HOST, PORT))
        sock.listen()

        try:
            sock, address = sock.accept()
            print('Connection established with ', address)
            data, parser = receive_data_from_socket(sock)

            print("Method:", parser.get_method())
            if parser.get_method() == "CONNECT":
                continue
            print("HTTP request detected")
            start_new_thread(proxy_http, (data, parser, sock, DB))

        except KeyboardInterrupt:
            sock.close()
            exit()
        except Exception as e:
            sock.close()
            print(e.args)
            exit()
