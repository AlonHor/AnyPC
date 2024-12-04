__author__ = "Alon & K9"

from enum import Enum
from events import Error, Events
from terminal import Terminal

import global_utils
import socket
import threading
import msvcrt
import struct

class DataType(Enum):
    Raw = "RAW",
    Part = "PART"

class Connection:
    def __init__(self, type: socket.SocketKind, addr: tuple[str, int]):
        self.socket = socket.socket(type=type)
        self.addr = addr

        NetworkUtils.add_listener(Events.UnknownEvent, UnknownEvent, DataType.Raw)
        NetworkUtils.add_listener(Events.OperationFailed_Response, ErrorEvent, DataType.Raw)
        NetworkUtils.add_listener(Events.OperationSuccess_Response, SuccessEvent, DataType.Raw)
        NetworkUtils.add_listener(Events.ConnectionClosed, ConnectionClosedEvent, DataType.Raw)

        self.socket.connect(self.addr)

        primary_connection = NetworkUtils.get_primary_connection()

        if primary_connection is None:
            Terminal.success(f"connected to [{self.addr[0]}:{self.addr[1]}].")

        NetworkUtils.listen_for_events(self.socket, self)

    def send(self, data: list):
        NetworkUtils.send_parts(self.socket, data, self.addr)

    def send_raw(self, data: bytes):
        match self.socket.type:
            case socket.SOCK_DGRAM:
                self.socket.sendto(data, self.addr)
            case socket.SOCK_STREAM:
                self.socket.send(data)

    def send_event(self, event_id: Events, data: list):
        global ongoing_requests

        global_utils.increment_requests()
        Terminal.debug(f"sending: [{event_id}] alongside {data} with [{global_utils.get_requests()}] ongoing requests...")

        data_to_send = [event_id.value]
        data_to_send += data
        self.send(data_to_send)

    def close(self):
        self.socket.close()

class Event:
    def __init__(self, connection: Connection):
        self.connection = connection

    def handle(self, data: list[bytes]):
        pass

class Request:
    def __init__(self, connection: Connection):
        self.connection = connection

class UnknownEvent(Event):
    def __init__(self, connection):
        super().__init__(connection)

    def handle(self, data: list[bytes]):
        Terminal.debug(f"unknown event: {[d.decode() for d in data]}.")

class ConnectionClosedEvent(Event):
    def __init__(self, connection):
        super().__init__(connection)

    def handle(self, data: list[bytes]):
        primary_connection = NetworkUtils.get_primary_connection()

        self.connection.close()

        if primary_connection is not None and self.connection.addr == primary_connection.addr:
            Terminal.error("connection closed.")
            global_utils.exit()

class ErrorEvent(Event):
    def __init__(self, connection):
        super().__init__(connection)

    def handle(self, data: list[bytes]):
        global ongoing_requests

        error_id = int.from_bytes(data[0])
        error = Error.from_value(error_id)

        Terminal.error(f"server responded with error: [{str(error)}].")
        global_utils.decrement_requests()

        Terminal.debug(f"error with [{global_utils.get_requests()}] ongoing requests.")

class SuccessEvent(Event):
    def __init__(self, connection):
        super().__init__(connection)

    def handle(self, data: list[bytes]):
        global ongoing_requests

        global_utils.decrement_requests()

        Terminal.debug(f"success with [{global_utils.get_requests()}] ongoing requests.")

class NetworkUtils:
    SIZE_OF_SIZE = 4
    SIZE_OF_SIZE_STRUCT = "I"
    SEPERATOR = b"\0"
    actions: dict[Events, tuple[type[Event], DataType]] = {}
    primary_connection: Connection | None = None

    @staticmethod
    def set_primary_connection(connection: Connection):
        NetworkUtils.primary_connection = connection

    @staticmethod
    def get_primary_connection() -> Connection | None:
        return NetworkUtils.primary_connection

    @staticmethod
    def close(s: socket.socket):
        s.shutdown(socket.SHUT_RDWR)
        s.close()

    @staticmethod
    def __recieve_raw(src: socket.socket) -> bytes | None:
        data = None
        try:
            match src.type:
                case socket.SOCK_STREAM:
                    size_bytes = b""
                    for _ in range(NetworkUtils.SIZE_OF_SIZE):
                        b = src.recv(1)
                        if b == b"": return None
                        size_bytes += b

                    size = struct.unpack(NetworkUtils.SIZE_OF_SIZE_STRUCT, size_bytes)[0]

                    data_bytes = b""
                    for _ in range(size):
                        b = src.recv(1)
                        if b == b"": return None
                        data_bytes += b

                    data = data_bytes

                case socket.SOCK_DGRAM:
                    try:
                        data_bytes, _ = src.recvfrom(65535)

                        data = data_bytes
                    except Exception as e:
                        Terminal.error(f"error at __recieve_raw UDP: {e}.")
                        pass

        except WindowsError:
            pass
        except Exception as e:
            Terminal.error(f"error at __recieve_raw: {e}.")

        return data

    @staticmethod
    def recieve_parts(src: socket.socket) -> tuple[list[bytes], list[bytes]] | None:
        raw_data = NetworkUtils.__recieve_raw(src)

        if raw_data is None: return None

        sep_parts = raw_data.split(NetworkUtils.SEPERATOR)
        raw_parts = raw_data.split(NetworkUtils.SEPERATOR, 1)

        return (sep_parts, raw_parts)

    @staticmethod
    def __send_raw(dst: socket.socket, bts: bytes, addr: tuple[str, int]):
        try:
            size_encoded = struct.pack(NetworkUtils.SIZE_OF_SIZE_STRUCT, len(bts))
            match dst.type:
                case socket.SOCK_STREAM:
                    data = size_encoded + bts
                    dst.sendall(data)
                    return True
                case socket.SOCK_DGRAM:
                    dst.sendto(size_encoded, addr)
                    dst.sendto(bts, addr)
                    return True

            return False
        except Exception as e:
            Terminal.error(f"error at __send_raw: {e}.")
            return False

    @staticmethod
    def send_parts(dst: socket.socket, parts: list, addr: tuple[str, int]):
        str_parts_encoded = [b if type(b) != str else b.encode() for b in parts]
        parts_encoded = [b if type(b) != int else b.to_bytes() for b in str_parts_encoded]
        bts = NetworkUtils.SEPERATOR.join(parts_encoded)
        return NetworkUtils.__send_raw(dst, bts, addr)

    @staticmethod
    def add_listener(event_id: Events, event: type[Event], data_type: DataType = DataType.Part):
        NetworkUtils.actions[event_id] = (event, data_type)

    @staticmethod
    def remove_listener(event_id: Events):
        del NetworkUtils.actions[event_id]

    @staticmethod
    def __callback_event(event_id: Events, data: list[bytes], raw_data: list[bytes], connection: Connection):
        Terminal.debug(f"recieved: [{event_id}] with [{global_utils.get_requests()}] ongoing requests.")

        action = NetworkUtils.actions.get(event_id)

        if action == None:
            NetworkUtils.__callback_event(Events.UnknownEvent, data, raw_data, connection)
            return

        event, data_type = action

        data_to_use = data if data_type == DataType.Part else raw_data

        event(connection).handle(data_to_use)

    @staticmethod
    def listen_for_events(s: socket.socket, connection: Connection):
        def thread():
            while True:
                try:
                    parts = NetworkUtils.recieve_parts(s)
                    if parts is None:
                        if s.type == socket.SOCK_DGRAM:
                            continue
                        NetworkUtils.__callback_event(Events.ConnectionClosed, [], [], connection)
                        break

                    sep_parts, raw_parts = parts

                    try:
                        event_id_str: str = sep_parts[0].decode()
                        event_id: Events = Events.from_value(event_id_str)

                        NetworkUtils.__callback_event(event_id, sep_parts[1:], raw_parts[1:], connection)
                    except:
                        Terminal.debug(f"bad event while decoding first part.")
                except Exception as e:
                    Terminal.error(f"error at listen_for_events: {e}.")

        threading.Thread(target=thread, daemon=True).start()
