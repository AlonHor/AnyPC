__author__ = "Alon & K9"

from typing import Any
from events import Events
from utils import Connection, DataType, Event, NetworkUtils
from terminal import Terminal
from constants import Constants
from pynput import keyboard

import numpy as np

import win32api
import threading
import global_utils
import socket
import req
import struct
import os
import pickle
import pyautogui
import time
import cv2
import av

is_controlling = False
is_watching = False

frame_width = 1920
frame_height = 1080
new_height = 1080
screen_width = win32api.GetSystemMetrics(0)
current_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
codec: Any = av.CodecContext.create('h264', 'r')

def normalize_mouse_position(pos: int, screen_size: int, accuracy: int) -> int:
    pos = global_utils.clamp(pos, 0, screen_size)
    normalized = int(pos * accuracy // screen_size)
    return global_utils.clamp(normalized, 0, accuracy - 1)

class ScreenshotDoneEvent(Event):
    def handle(self, data: list[bytes]):
        file_name = data[0].decode()

        Terminal.info(f"screenshot is done and is at [{file_name}]")
        should_download = Terminal.ask("download the screenshot?", True)

        if not should_download:
            return

        Terminal.info("downloading screenshot...")
        req.FileContentRequest(self.connection).handle(file_name)

class ScreenWatchAcceptedEvent(Event):
    def handle(self, data: list[bytes]):
        def t():
            global current_frame, frame_width, frame_height, screen_width, new_height, is_watching

            frame_width = struct.unpack("I", data[0][:4])[0]
            frame_height = struct.unpack("I", data[0][5:9])[0]
            current_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
            aspect_ratio = frame_width / frame_height
            new_height = int(screen_width / aspect_ratio)

            Terminal.info(f"screen watch accepted. {frame_width}, {frame_height}")

            screen_frame_connection = Connection(socket.SOCK_STREAM, (Constants.SERVER_IP, Constants.SCREEN_FRAME_PORT))

            NetworkUtils.add_listener(Events.ScreenFrame_Action, ScreenFrameEvent, DataType.Raw)

            Terminal.info("creating window...")

            cv2.namedWindow("screen", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("screen", frame_width, frame_height)
            cv2.setWindowTitle("screen", "Screen")
            cv2.moveWindow("screen", 0, 0)
            cv2.imshow("screen", current_frame)
            cv2.startWindowThread()

            Terminal.info("created window.")

            screen_frame_connection.send_raw(b"READY")

            is_watching = True
            while is_watching:
                try:
                    cv2.imshow("screen", cv2.resize(current_frame, (screen_width, new_height)))

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        is_watching = False

                except Exception as e:
                    Terminal.error(f"error while watching screen: {e}.")
                    is_watching = False

                time.sleep(1 / Constants.TO_SCREEN_UPDATE_RATE)

            primary_connection = NetworkUtils.get_primary_connection()
            if primary_connection is not None:
                req.ScreenWatchDisconnectActionRequest(primary_connection).handle()

            NetworkUtils.remove_listener(Events.ScreenFrame_Action)

            cv2.destroyAllWindows()

            # screen_frame_connection.close()

            Terminal.info(f"screen watch ended. [{global_utils.get_requests()}] ongoing.")
            global_utils.decrement_requests()
            global_utils.decrement_requests()

        threading.Thread(target=t).start()

class ScreenControlAcceptedEvent(Event):
    def handle(self, data: list[bytes]):
        def t():
            global current_frame, frame_width, frame_height, screen_width, new_height, is_controlling

            frame_width = struct.unpack("I", data[0][:4])[0]
            frame_height = struct.unpack("I", data[0][5:9])[0]
            current_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
            aspect_ratio = frame_width / frame_height
            new_height = int(screen_width / aspect_ratio)

            Terminal.info(f"screen control accepted. {frame_width}, {frame_height}")

            screen_frame_connection = Connection(socket.SOCK_STREAM, (Constants.SERVER_IP, Constants.SCREEN_FRAME_PORT))
            mouse_connection = Connection(socket.SOCK_DGRAM, (Constants.SERVER_IP, Constants.MOUSE_UPDATE_PORT))

            keyboard_connection = Connection(socket.SOCK_STREAM, (Constants.SERVER_IP, Constants.KEYBOARD_UPDATE_PORT))

            def on_press(key: keyboard.Key | keyboard.KeyCode | None): on_keyboard(key, True)
            def on_release(key: keyboard.Key | keyboard.KeyCode | None): on_keyboard(key, False)

            def on_keyboard(key: keyboard.Key | keyboard.KeyCode | None, is_press: bool):
                if key is None: return

                key_name: str = ""
                if type(key) == keyboard.KeyCode:
                    char = key.char
                    if char is None: key_name = str(char)
                    else: key_name = char
                if type(key) == keyboard.Key:
                    key_name = key.name

                if key_name == "q": return

                try:
                    req.ScreenControlKeyboardInputActionRequest(keyboard_connection).handle(is_press, key_name)
                except Exception as e:
                    Terminal.error(f"error while sending keyboard input (is_press: {is_press}): {e}.")
                finally:
                    global_utils.decrement_requests()

            listener = keyboard.Listener(on_press=on_press, on_release=on_release)

            listener.start()
            global_utils.start_listener()
            NetworkUtils.add_listener(Events.ScreenFrame_Action, ScreenFrameEvent, DataType.Raw)

            Terminal.info("creating window...")

            cv2.namedWindow("screen", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("screen", frame_width, frame_height)
            cv2.setWindowTitle("screen", "Screen")
            cv2.setWindowProperty("screen", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.moveWindow("screen", 0, 0)
            cv2.imshow("screen", current_frame)
            cv2.startWindowThread()

            Terminal.info("created window.")

            screen_frame_connection.send_raw(b"READY")

            is_controlling = True

            while is_controlling:
                try:
                    pos = pyautogui.position()
                    x_pos, y_pos = (int(pos[0]), int(pos[1]))
                    width, height = pyautogui.size()

                    mouse_state = global_utils.get_mouse_state()
                    mouse_button = global_utils.get_mouse_button()

                    x = normalize_mouse_position(x_pos, width, Constants.MOUSE_POSITION_ACCURACY)
                    y = normalize_mouse_position(y_pos, height, Constants.MOUSE_POSITION_ACCURACY)

                    req.ScreenControlMouseInputActionRequest(mouse_connection).handle(mouse_state, mouse_button, x, y)
                    global_utils.decrement_requests()

                    cv2.imshow("screen", cv2.resize(current_frame, (screen_width, new_height)))

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        is_controlling = False

                except Exception as e:
                    Terminal.error(f"error while tracking mouse position: {e}.")
                    is_controlling = False

                time.sleep(1 / Constants.TO_SCREEN_UPDATE_RATE)

            primary_connection = NetworkUtils.get_primary_connection()
            if primary_connection is not None:
                req.ScreenControlDisconnectActionRequest(primary_connection).handle()

            listener.stop()
            global_utils.stop_listener()
            NetworkUtils.remove_listener(Events.ScreenFrame_Action)

            cv2.destroyAllWindows()

            # screen_frame_connection.close()
            # mouse_connection.close()
            # keyboard_connection.close()

            Terminal.info(f"screen control ended. [{global_utils.get_requests()}] ongoing.")
            global_utils.decrement_requests()
            global_utils.decrement_requests()

        threading.Thread(target=t).start()

class ScreenFrameEvent(Event):
    @staticmethod
    def decode_frame(data):
        global codec
        try:
            packet = av.Packet(data)
            frames = codec.decode(packet)

            return [frame.to_ndarray(format='bgr24') for frame in frames]

        except Exception as e:
            Terminal.error(f"error while decoding frame: {e}.")
            return []

    def handle(self, data: list[bytes]):
        global current_frame, frame_width, frame_height, screen_width, new_height, is_controlling, is_watching

        if not (is_controlling or is_watching): return

        packet_data = data[0]

        frames = ScreenFrameEvent.decode_frame(packet_data)

        for frame in frames:
            if frame is not None:
                current_frame = frame

                cv2.imshow("screen", cv2.resize(current_frame, (screen_width, new_height)))
                cv2.waitKey(1)

class FileDownloadEvent(Event):
    def handle(self, data: list[bytes]):
        info = data[0].split(NetworkUtils.SEPERATOR, 3)

        tid = info[0]
        curr_chunk = int.from_bytes(info[1])
        total_chunks = int.from_bytes(info[2])
        chunk = info[3]

        Terminal.debug(f"total chunks: [{total_chunks}].")
        Terminal.debug(f"received chunk [{curr_chunk}].")

        loaded_bars = int(curr_chunk / total_chunks * 30)
        unloaded_bars = 30 - loaded_bars
        Terminal.info(f"download in progress: [{'#' * loaded_bars}{'_' * unloaded_bars}] {round(curr_chunk / total_chunks * 100, 2)}%    ",
            (curr_chunk != total_chunks))

        if tid in req.tid_map:
            file_name = os.path.basename(req.tid_map[tid])

            if not os.path.exists("downloads"):
                os.mkdir("downloads")

            path = os.path.join("downloads", file_name)

            with open(path, "ab") as file:
                file.write(chunk)

class FileListEvent(Event):
    def handle(self, data: list[bytes]):
        file_list_encoded = data[0]
        file_list = pickle.loads(file_list_encoded)
        for file in file_list:
            Terminal.out(file)

class CommandRunEvent(Event):
    def handle(self, data: list[bytes]):
        output = data[0].decode()
        Terminal.out(output)
