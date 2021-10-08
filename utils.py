import socket
import json
import ssl


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


def open_listen_socket(host: str, port: int) -> socket:
    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Re-use the socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind the socket to a static host, and a port
    sock.bind((host, port))
    sock.listen()
    return sock


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
