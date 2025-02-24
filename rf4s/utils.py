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


def initialize_setting_and_monitor(args_map: tuple[tuple]):
    """Initialize a setting node and a screen monitor for given application.

    This is a simple decorator that used for constructors in harvest and craft modules.

    :param args_map: args lookup table
    :type args_map: tuple[tuple]
    """
    #TODO
    def func_wrapper(func):
        def args_wrapper(caller):
            args = caller.parse_args()
            caller.setting = Setting()
            caller.setting.merge_args(args, args_map)
            caller.monitor = Detection(caller.setting)
            func(caller)

        return args_wrapper

    return func_wrapper


def toggle_clicklock(func):
    """Toggle clicklock before and after calling the function."""

    def wrapper(self, *args):
        pag.mouseDown()
        sleep(BASE_DELAY + LOOP_DELAY)
        try:
            func(self, *args)
            pag.click()
        except Exception as e:
            pag.click()
            raise e

    return wrapper


def toggle_right_mouse_button(func):
    """Toggle clicklock before and after calling the function."""

    def wrapper(self, *args):
        pag.mouseDown(button="right")
        try:
            func(self, *args)
            pag.mouseUp(button="right")
        except Exception as e:
            pag.mouseUp(button="right")
            raise e

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

    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
            release_keys()
        except Exception as e:
            release_keys()
            raise e

    return wrapper


# there's lots of early return in player._resetting_stage(),
# so use a decorator here to simplify the code
def reset_friction_brake_after(func):
    """Reset friction brake after calling the function."""

    def wrapper(self, *args):
        func(self, *args)
        if not self.cfg.ARGS.FRICTION_BRAKE:
            return

        with self.friction_brake_lock:
            self.friction_brake.reset(
                self.cfg.FRICTION_BRAKE.INITIAL)

    return wrapper
