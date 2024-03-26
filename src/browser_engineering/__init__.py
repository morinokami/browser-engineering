import tkinter

from .browser import URL, Browser


def main() -> int:
    import sys

    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

    return 0
