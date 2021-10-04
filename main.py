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


def receive_data_from_socket(sock):
    parser = HttpParser()
    resp = b''
    while not parser.is_message_complete():
        data = sock.recv(BUF_SIZE)
        if not data:
            break

        parser.execute(data, len(data))

        resp += data
    return resp, parser


def cleanup_http_request(parser, data):
    data_array = data.decode("utf-8").split("\r\n")
    print(data_array)
    url = ""
    if parser.is_headers_complete():
        url = parser.get_url()

    if len(data_array) < 2:
        return None, None
    data_array[0] = data_array[0].replace(url, parser.get_path())

    host = parser.get_headers()['host'].strip()

    request_to_host = ""
    for line in data_array:
        if line.find("Proxy-Connection") != -1:
            request_to_host += "Connection: close\r\n"
        # elif line.find("Accept-Encoding: gzip, deflate") != -1:
        #     request_to_host += "Accept-Encoding: deflate\r\n"
        else:
            request_to_host += line + "\n"

    return request_to_host, host


def http_request(request, host, port):
    sock_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock_req.connect((host, port))
    except:
        sock_req.close()
        return None
    sock_req.sendall(request.encode("utf-8"))
    return sock_req


def proxy_http(data, parser, sock, DB):
    request, host = cleanup_http_request(parser, data)
    reply = recv_from_host(request, host, 80)
    sock.sendall(reply)
    sock.close()
    DB.insert_request(request, host, 0)
    return reply


def recv_from_host(request, host, port):
    sock_req = http_request(request, host, port)
    if not sock_req:
        return None
    reply, _ = receive_data_from_socket(sock_req)
    sock_req.close()
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
            data, parser = receive_data_from_socket(sock)

            if parser.get_method() == "CONNECT":
                print("HTTPS request detected")
                sock.close()
            else:
                print("Method:", parser.get_method())
                print("HTTP request detected")
                start_new_thread(proxy_http, (data, parser, sock, DB))

        except KeyboardInterrupt:
            sock.close()
            exit()
        except Exception as e:
            sock.close()
            print(e.args)
