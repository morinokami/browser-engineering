import socket
import ssl
import tkinter


class URL:
    def __init__(self, url: str) -> None:
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
        request = f"GET {self.path} HTTP/1.0\r\n"
        request += f"Host: {self.host}\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))

        # read the response from the server
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        # split the status line into parts (the HTTP version, the status code, and a reason phrase)
        statusline = response.readline()  # HTTP/1.0 200 OK
        version, status, expalanation = statusline.split(" ", 2)

        # read the headers
        response_headers: dict[str, str] = {}
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
        content = response.read()
        s.close()

        return content


def lex(body: str) -> str:
    """
    Return the textual content of an HTML document without printing it.
    """
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


def layout(text: str) -> list[tuple[int, int, str]]:
    """
    Compute and store the position of each character.
    """
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP

    return display_list


class Browser:
    def __init__(self) -> None:
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url: URL) -> None:
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, event: tkinter.Event) -> None:  # type: ignore
        self.scroll += SCROLL_STEP
        self.draw()
