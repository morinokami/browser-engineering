import socket
import ssl
from typing import Dict


class URL:
    def __init__(self, url: str):
        # separate the scheme from the rest of the URL
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

        # separate the host from the path
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # set the default port
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        # use a different port if it's specified in the URL
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self) -> str:
        # create a socket
        s = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )

        # connect to the server
        s.connect((self.host, self.port))

        # encrypt the connection if it's HTTPS
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # make a request to the server
        s.send(
            (f"GET {self.path} HTTP/1.0\r\n" + f"Host: {self.host}\r\n\r\n").encode(
                "utf8"
            )
        )

        # read the response from the server
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        # split the status line into parts (the HTTP version, the status code, and a reason phrase)
        statusline = response.readline()  # HTTP/1.0 200 OK
        version, status, expalanation = statusline.split(" ", 2)

        # read the headers
        response_headers: Dict[str, str] = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # these haeders are not supported
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # read the body
        body = response.read()
        s.close()

        return body


def show(body: str) -> None:
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")


def load(url: URL) -> None:
    body = url.request()
    show(body)
