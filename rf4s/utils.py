"""
Some helper functions.
"""

import logging
import sys
from time import sleep

import pyautogui as pag
from prettytable import PrettyTable
from pyscreeze import Box

from rf4s.controller.detection import Detection

# BASE_DELAY + LOOP_DELAY >= 2.2 to trigger clicklock
BASE_DELAY = 0.2
LOOP_DELAY = 2

ANIMATION_DELAY = 1

logger = logging.getLogger("rich")

# ---------------------------------------------------------------------------- #
#                            common functionalities                            #
# ---------------------------------------------------------------------------- #


def hold_mouse_button(duration: float=1, button="left") -> None:
    """Hold left or right mouse button.

    :param duration: hold time, defaults to 1
    :type duration: float, optional
    :param button: button to click, defaults to "left"
    :type button: str, optional
    """
    if duration == 0:
        return

    pag.mouseDown(button=button)
    sleep(duration)
    pag.mouseUp(button=button)
    if button == "left" and duration >= 2.1:  # + 0.1 due to pag.mouseDown() delay
        pag.click()

def hold_mouse_buttons(duration: float = 1) -> None:
    """Hold left mouse button.

    :param duration: hold time, defaults to 1
    :type duration: float, optional
    """
    pag.mouseDown()
    pag.mouseDown(button="right")
    sleep(duration)
    pag.mouseUp()
    pag.mouseUp(button="right")
    if duration >= 2.1:  # + 0.1 due to pag.mouseDown() delay
        pag.click()


def sleep_and_decrease(num: int, delay: int) -> int:
    """Self-decrement with a delay.

    :param num: the variable to decrease
    :type num: int
    :param delay: sleep time
    :type delay: int
    :return: decreased num
    :rtype: int
    """
    sleep(delay)
    return num - delay


def ask_for_confirmation(msg: str = "Ready to start") -> None:
    """Ask for confirmation of user settings if it's enabled.

    :param msg: confirmation message, defaults to "Ready to start"
    :type msg: str
    """
    while True:
        ans = input(f"{msg}? [Y/n] ").strip().lower()
        if ans in ("y", ""):
            break
        if ans == "n":
            sys.exit()


def display_running_results(app: object, result_map: tuple[tuple]) -> None:
    """Display the running results of different apps.

    :param app: caller object
    :type app: object
    :param result_map: attribute name - column name mapping
    :type result_map: tuple[tuple]
    """
    table = PrettyTable(header=False, align="l")
    table.title = "Running Results"
    # table.field_names = ['Record', 'Value']
    for attribute_name, column_name in result_map:
        table.add_row([column_name, getattr(app, attribute_name)])
    print(table)


def get_box_center(box: Box) -> tuple[int, int]:
    """Get the center coordinate (x, y) of the given box.

    # (x, y, w, h) -> (x, y), np.int64 -> int

    :param box: box coordinates (x, y, w, h)
    :type box: Box
    :return: x and y coordinates of the center point
    :rtype: tuple[int, int]
    """
    return int(box.left + box.width // 2), int(box.top + box.height // 2)


def start_app(app: object, results: tuple[tuple]) -> None:
    """A wrapper for confirmation, window activatioin, and start.

    :param app: main application class
    :type app: object
    :param results: counter lookup table
    :type results: tuple[tuple]
    """

    if app.setting.confirmation_enabled:
        ask_for_confirmation()
    app.setting.window_controller.activate_game_window()
    try:
        app.start()
    except KeyboardInterrupt:
        pass

    if results is not None:
        display_running_results(app, results)
    app.setting.window_controller.activate_script_window()


# ---------------------------------------------------------------------------- #
#                                  decorators                                  #
# ---------------------------------------------------------------------------- #


def toggle_clicklock(func):
    """Toggle clicklock before and after calling the function."""

    def wrapper(*args, **kwargs):
        pag.mouseDown()
        sleep(BASE_DELAY + LOOP_DELAY)
        try:
            func(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            pag.click()

    return wrapper


def toggle_right_mouse_button(func):
    """Toggle right mouse button before and after calling the function."""

    def wrapper(*args, **kwargs):
        pag.mouseDown(button="right")
        try:
            func(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            pag.mouseUp(button="right")

    return wrapper


def press_key_before_and_after(func):
    def wrapper(*args, **kwargs):
        pag.press(kwargs.get("_key"))
        sleep(ANIMATION_DELAY)
        try:
            func(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            pag.press(kwargs.get("_key"))
            sleep(ANIMATION_DELAY)

    return wrapper


def hold_key(func):
    def wrapper(*args, **kwargs):
        pag.keyDown(kwargs.get("_key"))
        sleep(ANIMATION_DELAY)
        try:
            func(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            pag.keyUp(kwargs.get("_key"))
            sleep(ANIMATION_DELAY)

    return wrapper



def release_keys_after(func):
    """Release keys that might have been holding down."""
    def release_keys():
        pag.keyUp("ctrl")
        pag.keyUp("ctrl")
        pag.keyUp("shift")
        pag.keyUp("w")
        pag.keyUp("a")
        pag.keyUp("d")

    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
            release_keys()
        except Exception as e:
            raise e
        finally:
            release_keys()

    return wrapper


# there's lots of early return in player._resetting_stage(),
# so use a decorator here to simplify the code
def reset_friction_brake_after(func):
    """Reset friction brake after calling the function."""
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        if not self.cfg.ARGS.FRICTION_BRAKE:
            return

        with self.friction_brake_lock:
            self.friction_brake.reset(
                self.cfg.FRICTION_BRAKE.INITIAL)

    return wrapper
