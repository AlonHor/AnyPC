__author__ = "Alon & K9"

from terminal import Terminal, Colors

class Parser:
    @staticmethod
    def parse_command(command_string) -> tuple[str, list[str]] | None:
        parts = command_string.strip().split()

        if not parts:
            Terminal.warning("no command entered.")
            return None

        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        return (cmd, args)
