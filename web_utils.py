import ssl
import gzip
import socket
try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser


RECV_TIMEOUT = 2
BUF_SIZE = 4096


def open_listen_socket(host: str, port: int) -> socket:
    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Re-use the socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind the socket to a static host, and a port
    sock.bind((host, port))
    sock.listen()
    return sock


def receive_data(sock: socket, parser: HttpParser) -> bytes:
    data = b""
    sock.settimeout(RECV_TIMEOUT)
    while not parser.is_message_complete():
        chunk = None
        try:
            chunk = sock.recv(BUF_SIZE)
        except:
            if parser.is_headers_complete():
                break
        if not chunk:
            break

        parser.execute(chunk, len(chunk))
        data += chunk
    return data


def headers_to_string(headers: dict, ignore_headers: list = []):
    sv_request = ""
    for header, value in headers.items():
        if header.lower() not in ignore_headers:
            sv_request += header + ": " + value + "\n"
    return sv_request


def http_request(request: (str, bytes), host: str, secure: bool = False, gzip_decode: bool = False, port: int = None) -> (bytes, HttpParser):
    if not port:
        port = 443 if secure else 80

    sv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sv_sock.connect((host, port))

    if secure:
        sv_sock = ssl.create_default_context().wrap_socket(sv_sock, server_hostname=host)

    if isinstance(request, bytes):
        sv_sock.sendall(request + b'\r\n\r\n')
    else:
        sv_sock.sendall((request + '\n\n').replace(' \n', '\r\n').encode())

    sv_parser = HttpParser()
    sv_reply = receive_data(sv_sock, sv_parser)
    sv_sock.close()

    if not gzip_decode:
        return sv_reply, sv_parser

    # decode from gzip
    headers = sv_parser.get_headers()
    headers_and_body = sv_reply.split(b'\r\n\r\n')
    if len(headers_and_body) > 1 and headers.get('content-encoding') == "gzip":
        recv_body = headers_and_body[1]
        sv_reply = sv_reply[:sv_reply.find(b'\r\n')].strip() + b'\n'  # HTTP/1.1 200
        sv_reply += headers_to_string(headers, ['content-encoding', 'transfer-encoding']).replace('\n', '\r\n').encode() + b'\r\n'
        if sv_parser.is_chunked():
            splitted_body = recv_body.split(b'\r\n')
            recv_body = b''
            for i in range(1, len(splitted_body), 2):
                recv_body += splitted_body[i]
        recv_body = gzip.decompress(recv_body)
        sv_reply += recv_body
    return sv_reply, sv_parser
