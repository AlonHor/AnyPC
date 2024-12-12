from pynput import mouse
from terminal import Terminal
import msvcrt
import sys

__ongoing_requests: int = 0
__mouse_state: int = 0
__mouse_button: int = 0
__mouse_listener: mouse.Listener
__use_rsa: bool = False

def decrement_requests():
    global __ongoing_requests

    __ongoing_requests -= 1
    if __ongoing_requests < 0:
        __ongoing_requests = 0

    return __ongoing_requests

def increment_requests():
    global __ongoing_requests

    __ongoing_requests += 1
    return __ongoing_requests

def get_requests():
    return __ongoing_requests

def set_requests(n: int):
    global __ongoing_requests

    __ongoing_requests = n

def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))

def on_click(x, y, button: mouse.Button, pressed: bool):
    global __mouse_state, __mouse_button
    __mouse_state = 1 if pressed else 0
    __mouse_button = 1 if button == mouse.Button.left else (2 if button == mouse.Button.right else (3 if button == mouse.Button.middle else 0))

def on_scroll(x, y, dx, dy):
    global __mouse_state
    if dy > 0:
        __mouse_state = 3
    else: __mouse_state = 2

def start_listener():
    global __mouse_listener
    __mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    __mouse_listener.start()

def stop_listener():
    __mouse_listener.stop()

def get_mouse_state():
    global __mouse_state
    prev = __mouse_state
    if __mouse_state in [2, 3]:
        __mouse_state = 0
    return prev

def get_mouse_button():
    return __mouse_button

def enable_rsa():
    global __use_rsa
    __use_rsa = True
    Terminal.debug("enabled rsa.")

def disable_rsa():
    global __use_rsa
    __use_rsa = False

def get_is_rsa():
    return __use_rsa

def exit():
    try:
        while msvcrt.kbhit():
            msvcrt.getch()
    except:
        pass
    sys.exit()
