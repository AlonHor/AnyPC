__author__ = "Alon & K9"

from constants import Constants
from utils import Connection, NetworkUtils, Request
from terminal import Terminal
from events import Events

import os
import math
import global_utils

tid_map: dict[bytes, str] = {}

class ScreenshotRequest(Request):
    def handle(self):
        self.connection.send_event(Events.Screenshot_Request, [])

class ScreenControlRequest(Request):
    def handle(self):
        self.connection.send_event(Events.ScreenControl_Request, [])

class ScreenWatchRequest(Request):
    def handle(self):
        self.connection.send_event(Events.ScreenWatch_Request, [])

class ScreenControlMouseInputActionRequest(Request):
    def handle(self, mouse_state: int, mouse_button: int, x: int, y: int):
        x_encoded, y_encoded = x.to_bytes(2), y.to_bytes(2)
        mouse_state_encoded, mouse_button_encoded = mouse_state.to_bytes(), mouse_button.to_bytes()
        self.connection.send_event(Events.ScreenControlInput_Action, [mouse_state_encoded + mouse_button_encoded + x_encoded + y_encoded])

class ScreenControlKeyboardInputActionRequest(Request):
    def handle(self, is_press: bool, key: str):
        Terminal.debug(f"key: {key}, pressed: {is_press}")
        self.connection.send_event(Events.ScreenControlInput_Action, [1 if is_press else 2, key])

class ScreenControlDisconnectActionRequest(Request):
    def handle(self):
        self.connection.send_event(Events.ScreenControlDisconnect_Action, [])

class ScreenWatchDisconnectActionRequest(Request):
    def handle(self):
        self.connection.send_event(Events.ScreenWatchDisconnect_Action, [])

class FileContentRequest(Request):
    def handle(self, file_name: str):
        tid = os.urandom(4)
        while tid in tid_map: tid = os.urandom(4)
        tid_map[tid] = file_name
        if os.path.exists(file_name):
            with open(file_name, "rb") as file:
                file.flush()

        self.connection.send_event(Events.FileContent_Request, [tid, file_name])

class FileListRequest(Request):
    def handle(self, path: str):
        self.connection.send_event(Events.FileList_Request, [path])

class CopyFileRequest(Request):
    def __init__(self, connection: Connection):
        super().__init__(connection)

    def handle(self, src: str, dst: str):
        self.connection.send_event(Events.CopyFile_Request, [src, dst])

class MoveFileRequest(Request):
    def handle(self, src: str, dst: str):
        self.connection.send_event(Events.MoveFile_Request, [src, dst])

class RemoveFileRequest(Request):
    def handle(self, path: str):
        self.connection.send_event(Events.RemoveFile_Request, [path])

class RunCommandRequest(Request):
    def handle(self, command: str):
        self.connection.send_event(Events.CommandRun_Request, [command])

class FileUploadRequest(Request):
    def handle(self, local_path: str, path: str):
        if not os.path.exists(local_path):
            Terminal.error(f"file [{local_path}] does not exist.")
            return

        total_chunks = math.ceil(os.path.getsize(local_path) / Constants.CHUNK_SIZE)

        for i in range(total_chunks):
            with open(local_path, "rb") as file:
                file.seek(i * Constants.CHUNK_SIZE)
                chunk = file.read(Constants.CHUNK_SIZE)
                self.connection.send_event(Events.FileUpload_Action, [path, total_chunks, chunk])
            global_utils.decrement_requests()
