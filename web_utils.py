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
        sv_sock.sendall((request + '\n\n').replace('\n', '\r\n').encode())

    sv_parser = HttpParser()
    sv_reply = receive_data(sv_sock, sv_parser)
    sv_sock.close()

    if not gzip_decode:
        return sv_reply, sv_parser

    # decode from gzip
    headers = sv_parser.get_headers()
    headers_and_response = sv_reply.split(b'\r\n\r\n')
    decoded_body = headers_and_response[1]

    decoded_headers = sv_reply[:sv_reply.find(b'\r\n')] + b'\r\n'  # HTTP/1.1 200
    decoded_headers += headers_to_string(headers, ['transfer-encoding', 'content-encoding']).replace('\n', '\r\n').encode() + b'\r\n'
    if sv_parser.is_chunked():
        splitted_body = decoded_body.split(b'\r\n')
        decoded_body = b''
        for i in range(1, len(splitted_body), 2):
            decoded_body += splitted_body[i]

    if len(headers_and_response) > 1 and headers.get('content-encoding') == "gzip":
        decoded_body = gzip.decompress(decoded_body) + b'\n\n'

    return decoded_headers + decoded_body, sv_parser


def get_post_data(data: bytes) -> str:
    return data[data.rfind(b'\r\n\r\n') + len(b'\r\n\r\n'):].decode()


def split_request(host: str, parser: HttpParser) -> (str, str, str, str, str, str):
    headers = parser.get_headers()
    cleanup_headers(headers)
    wsgi = parser.get_wsgi_environ()
    str_headers = wsgi['REQUEST_METHOD'] + " " + wsgi['PATH_INFO'] + " " + wsgi['SERVER_PROTOCOL'] + "\n"
    str_headers += headers_to_string(headers, ['cookie'])
    str_headers.replace('\r', '')
    cookie = headers.get('COOKIE')
    return host, wsgi['REQUEST_METHOD'], host + parser.get_url(), str_headers, cookie.replace(' ', '\n') if cookie else None


def cleanup_headers(headers: dict):
    for header, value in headers.items():
        if header == "PROXY-CONNECTION":
            headers.pop(header)
            headers["CONNECTION"] = value
        elif header == "ACCEPT-ENCODING":
            headers[header] = value.replace('gzip', 'no_gzip_please')
        elif header in ["IF-MODIFIED-SINCE", "IF-NONE-MATCH"]:
            headers.pop(header)
