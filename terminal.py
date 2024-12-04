__author__ = "Alon & K9"

from enum import Enum
from constants import Constants

import os

class Colors(Enum):
    GRAY = "\033[90m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    RESET = "\033[0m"

class Terminal:
    @staticmethod
    def _colorize(text: str, color: Colors | None = None, bg_color: Colors | None = None, bold: bool = False, underline: bool = False):
        style = ""
        if bold:
            style += Colors.BOLD.value
        if underline:
            style += Colors.UNDERLINE.value
        if color:
            style += color.value
        if bg_color:
            style += bg_color.value

        return f"{style}{text}{Colors.RESET.value}"

    @staticmethod
    def info(text: str, flush: bool = False):
        print(Terminal._colorize(text, color=Colors.BLUE, bold=True) + ("\r" if flush else ""), flush=flush, end=("" if flush else "\n"))

    @staticmethod
    def debug(text: str):
        if Constants.DEBUG_MODE:
            print(Terminal._colorize(text, color=Colors.GRAY))

    @staticmethod
    def success(text: str):
        print(Terminal._colorize(text, Colors.GREEN, bold=True))

    @staticmethod
    def warning(text: str):
        print(Terminal._colorize(text, Colors.YELLOW))

    @staticmethod
    def error(text: str):
        print(Terminal._colorize(text, Colors.RED, bold=True))

    @staticmethod
    def out(text: str):
        print(Terminal._colorize(text, Colors.WHITE))

    @staticmethod
    def get_input(prompt: str = "> ", color: Colors | None = None):
        if color:
            prompt = Terminal._colorize(prompt, color)
        return input(prompt)

    @staticmethod
    def ask(question: str, default: bool = True) -> bool:
        default_str = "Y/n" if default else "y/N"
        question = f"{question} ({default_str}) "

        response = Terminal.get_input(question, Colors.YELLOW).lower()

        if not response:
            return default

        return response == "y"

    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def logo():
        print(Terminal._colorize(Constants.LOGO, color=Colors.GREEN, bold=True))
