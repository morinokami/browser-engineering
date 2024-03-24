from .browser import URL, load


def main() -> int:
    import sys

    load(URL(sys.argv[1]))

    return 0
