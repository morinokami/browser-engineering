import socket
import ssl
import tkinter
import tkinter.font
from typing import Literal


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


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


class Browser:
    def __init__(self) -> None:
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url: URL) -> None:
        body = url.request()
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        for x, y, c, f in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(x, y - self.scroll, text=c, anchor="nw", font=f)

    def scrolldown(self, event: tkinter.Event) -> None:  # type: ignore
        self.scroll += SCROLL_STEP
        self.draw()


class Text:
    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return "Text('{}')".format(self.text)


class Tag:
    def __init__(self, tag: str) -> None:
        self.tag = tag

    def __repr__(self) -> str:
        return "Tag('{}')".format(self.tag)


TokenType = Text | Tag


def lex(body: str) -> list[TokenType]:
    out: list[TokenType] = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer:
                out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer))
    return out


FontWeightType = Literal["normal", "bold"]
FontSlantType = Literal["roman", "italic"]

FONTS = {}


def get_font(
    size: int, weight: FontWeightType, slant: FontSlantType
) -> tkinter.font.Font:
    key = (size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]


DisplayListType = list[tuple[int, float, str, tkinter.font.Font]]


class Layout:
    def __init__(self, tokens: list[TokenType]) -> None:
        self.display_list: DisplayListType = []
        self.cursor_x = HSTEP
        self.cursor_y = float(VSTEP)
        self.weight: FontWeightType = "normal"
        self.style: FontSlantType = "roman"
        self.size = 16
        self.line: list[tuple[int, str, tkinter.font.Font]] = []
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok: TokenType) -> None:
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP

    def word(self, word: str) -> None:
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w >= WIDTH - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    def flush(self) -> None:
        if not self.line:
            return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []
