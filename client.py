__author__ = "Alon & K9"

from constants import Constants
from parser import Parser
from utils import NetworkUtils, Connection, DataType
from terminal import Colors, Terminal
from events import Events

import global_utils
import req
import socket
import time
import res

def wait():
    while global_utils.get_requests() != 0:
        time.sleep(0.1)

def wait_for_rsa():
    while not global_utils.get_is_rsa():
        time.sleep(0.1)

def main():
    Terminal.clear()
    Terminal.logo()

    Terminal.info("enter the server's IP address:")
    ip = Terminal.get_input("$ ", color=Colors.CYAN)

    Terminal.info("\nconnecting to server...")

    connection = None

    try:
        connection = Connection(socket.SOCK_STREAM, (ip, Constants.PRIMARY_CONNECTION_PORT))
    except Exception as e:
        Terminal.error(f"exiting, couldn't connect to server: {e}.")
        return

    NetworkUtils.set_primary_connection(connection)

    NetworkUtils.add_listener(Events.PublicKeyTransfer, res.PublicKeyTransferEvent, DataType.Raw)

    Terminal.info("establishing an encrypted connection...")

    wait_for_rsa()
    Terminal.success("key exchange completed, the connection is now end-to-end encrypted.")

    NetworkUtils.add_listener(Events.ScreenshotDone_Response, res.ScreenshotDoneEvent)
    NetworkUtils.add_listener(Events.AcceptScreenControl_Response, res.ScreenControlAcceptedEvent, DataType.Raw)
    NetworkUtils.add_listener(Events.AcceptScreenWatch_Response, res.ScreenWatchAcceptedEvent, DataType.Raw)
    NetworkUtils.add_listener(Events.FileDownload_Response, res.FileDownloadEvent, DataType.Raw)
    NetworkUtils.add_listener(Events.FileList_Response, res.FileListEvent, DataType.Raw)
    NetworkUtils.add_listener(Events.CommandRun_Response, res.CommandRunEvent)

    time.sleep(0.25)

    running = True

    while running:
        try:
            wait()
            print()
            command = Terminal.get_input("$ ", color=Colors.CYAN)

            if command == "exit":
                connection.send_event(Events.ConnectionClosed, [])
                connection.close()
                break

            parsed = Parser.parse_command(command)

            if parsed is None:
                continue

            cmd, args = parsed

            match cmd:
                case "echo":
                    Terminal.out(f"{' '.join(args)}")
                    continue

                case "mv":
                    if len(args) != 2:
                        Terminal.error("mv requires 2 arguments: source and destination.")
                        continue

                    Terminal.info(f"moving [{args[0]}] to [{args[1]}]...")
                    req.MoveFileRequest(connection).handle(args[0], args[1])
                    continue

                case "cp":
                    if len(args) != 2:
                        Terminal.error("cp requires 2 arguments: source and destination.")
                        continue

                    Terminal.info(f"copying [{args[0]}] to [{args[1]}]...")

                    req.CopyFileRequest(connection).handle(args[0], args[1])
                    continue

                case "rm":
                    if len(args) != 1:
                        Terminal.error("rm requires 1 path argument.")
                        continue

                    Terminal.info(f"removing [{args[0]}]...")
                    req.RemoveFileRequest(connection).handle(args[0])
                    continue

                case "upload":
                    if len(args) != 2:
                        Terminal.error("upload requires 2 path arguments, source and destination.")
                        continue

                    Terminal.info(f"uploading [{args[0]}] to [{args[1]}]...")
                    req.FileUploadRequest(connection).handle(args[0], args[1])
                    continue

                case "fetch":
                    if len(args) != 1:
                        Terminal.error("fetch requires 1 path argument.")
                        continue

                    Terminal.info(f"fetching from [{args[0]}]...")

                    req.FileContentRequest(connection).handle(args[0])
                    continue

                case "ss":
                    Terminal.info("taking screenshot...")

                    req.ScreenshotRequest(connection).handle()
                    continue

                case "sc":
                    Terminal.info("starting screen control...")

                    req.ScreenControlRequest(connection).handle()
                    continue

                case "sw":
                    Terminal.info("starting screen watch...")

                    req.ScreenWatchRequest(connection).handle()
                    continue

                case "ls":
                    Terminal.info("listing directory contents...")

                    req.FileListRequest(connection).handle(args[0] if args else ".")
                    continue

                case "run":
                    if len(args) == 0:
                        Terminal.error("run requires the command to run.")
                        continue

                    Terminal.info(f"running [{' '.join(args)}]...")
                    req.RunCommandRequest(connection).handle(" ".join(args))

                case "clear":
                    Terminal.clear()
                    continue

                case "cls":
                    Terminal.clear()
                    continue

                case "help":
                    Terminal.out("commands: echo, mv, cp, rm, upload, fetch, ss, sc, sw, ls, run, clear, cls, help, exit.")

                case _:
                    Terminal.error(f"unknown command: {cmd}.")
                    continue

        except KeyboardInterrupt:
            running = False
        except Exception as e:
            Terminal.error(f"an unexpected error occurred at main loop: {e}.")
            running = False

    connection.send_event(Events.ConnectionClosed, [])

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        Terminal.error(f"exiting, an unexpected error occurred outside of main loop: {e}.")
    finally:
        global_utils.exit()
