"""
Module for Tackle class and some decorators.

"""

# pylint: disable=c-extension-no-member

import logging
import random
from time import sleep

import pyautogui as pag
import win32api
import win32con

from rf4s import exceptions, utils
from rf4s.controller.detection import Detection
from rf4s.controller.timer import Timer

logger = logging.getLogger("rich")

RESET_TIMEOUT = 16
CAST_SCALE = 0.4  # 25% / 0.4s

# BASE_DELAY + LOOP_DELAY >= 2.2 to trigger clicklock
BASE_DELAY = 1
LOOP_DELAY = 2

ANIMATION_DELAY = 1

RETRIEVAL_TIMEOUT = 32
PULL_TIMEOUT = 16
RETRIEVAL_WITH_PAUSE_TIMEOUT = 128
LIFT_DURATION = 3
TELESCOPIC_RETRIEVAL_TIMEOUT = 8
LANDING_NET_DURATION = 6
LANDING_NET_DELAY = 0.5


OFFSET = 100
NUM_OF_MOVEMENT = 4


class Tackle:
    """Class for all tackle dependent methods."""

    def __init__(self, cfg, timer: Timer, detection: Detection):
        """Get timer and setting from caller (Player).

        :param setting: universal setting node
        :type setting: Setting
        :param setting: universal detection node
        :type setting: Monitor
        :param timer: object for timing methods
        :type timer: Timer
        """
        self.cfg = cfg
        self.timer = timer
        self.detection = detection
        self.landing_net_out = False  # for telescopic_pull()
        self.available = True

        if self.cfg.SELECTED.MODE == "telescopic":
            self._pull = self.telescopic_pull
        else:
            self._pull = self.general_pull

    @staticmethod
    def _check_status(func):
        def wrapper(self, *args, **kwargs):
            if not self.available:
                return
            try:
                func(self, *args)
            except Exception as e:
                raise e

        return wrapper

    @_check_status
    @utils.toggle_clicklock
    def reset(self) -> None:
        """Reset the tackle till ready and detect unexpected events.

        :raises exceptions.FishHookedError: a fish is hooked
        :raises exceptions.FishCapturedError: a fish is captured
        :raises exceptions.TimeoutError: loop timed out
        """
        logger.info("Resetting")
        i = RESET_TIMEOUT
        while i > 0:
            if self.detection.is_tackle_ready():
                return
            if self.detection.is_fish_hooked():
                raise exceptions.FishHookedError
            if self.detection.is_fish_captured():
                raise exceptions.FishCapturedError
            if self.cfg.SCRIPT.SPOOLING_DETECTION and self.detection.is_line_at_end():
                raise exceptions.LineAtEndError
            if self.cfg.SCRIPT.SNAG_DETECTION and self.detection.is_line_snagged():
                raise exceptions.LineSnaggedError
            i = utils.sleep_and_decrease(i, LOOP_DELAY)

        raise TimeoutError

    @_check_status
    def cast(self, lock) -> None:
        """Cast the rod, then wait for the lure/bait to fly and sink.

        :param update: update the record or not (for spod rod), defaults to True
        :type update: bool, optional
        """
        logger.info("Casting")
        if self.cfg.ARGS.MOUSE:
            self.move_mouse_randomly()
        match self.cfg.SELECTED.CAST_POWER_LEVEL:
            case 1:  # 0%
                pag.click()
            case 5:  # power cast
                with pag.hold("shift"):
                    utils.hold_mouse_button(1)
            case _:
                # -1 for backward compatibility
                duration = CAST_SCALE * (self.cfg.SELECTED.CAST_POWE_LEVEL - 1)
                utils.hold_mouse_button(duration)

        sleep(self.cfg.SELECTED.CAST_DELAY)
        if lock:
            pag.click()

    def sink(self) -> None:
        """Sink the lure until an event happend, designed for marine and wakey rig.

        :param marine: whether to check is lure moving in bottom layer, defaults to True
        :type marine: bool, optional
        """
        logger.info("Sinking")
        i = self.cfg.SELECTED.SINK_TIMEOUT
        while i > 0:
            i = utils.sleep_and_decrease(i, LOOP_DELAY)
            if self.detection.is_moving_in_bottom_layer():
                logger.info("Lure reached bottom layer")
                break

            if self.detection.is_fish_hooked_twice():
                logger.info("Fish hooked")
                pag.click()
                return

        utils.hold_mouse_button(self.cfg.SELECTED.TIGHTEN_DURATION)


    @_check_status
    @utils.toggle_clicklock
    @utils.release_keys_after
    def retrieve(self, first: bool = True) -> None:
        """Retrieve the line till the end is reached and detect unexpected events.

        :param first: whether it's invoked for the first time, defaults to True
        :type first: bool, optional
        :raises exceptions.FishCapturedError: a fish is captured
        :raises exceptions.LineAtEndError: line is at its end
        :raises exceptions.TimeoutError: loop timed out
        """
        logger.info("Retrieving")

        i = RETRIEVAL_TIMEOUT
        while i > 0:
            if self.detection.is_fish_hooked():
                if self.cfg.SELECTED.POST_ACCELERATION == "always":
                    pag.keyDown("shift")
                elif self.cfg.SELECTED.POST_ACCELERATION == "auto" and first:
                    pag.keyDown("shift")

                if self.cfg.ARGS.LIFT:
                    utils.hold_mouse_button(LIFT_DURATION, button="right")

            if self.detection.is_retrieve_finished():
                sleep(0 if self.cfg.ARGS.RAINBOW_LINE else 2)
                return

            elif self.detection.is_fish_captured():
                raise exceptions.FishCapturedError
            elif self.cfg.SCRIPT.SPOOLING_DETECTION and self.detection.is_line_at_end():
                raise exceptions.LineAtEndError
            elif self.cfg.SCRIPT.SNAG_DETECTION and self.detection.is_line_snagged():
                raise exceptions.LineSnaggedError
            i = utils.sleep_and_decrease(i, LOOP_DELAY)

        raise TimeoutError

    def retrieve_with_pause(self) -> None:
        """Retreive the line, pause periodically."""
        logger.info("Retrieving with pause")
        self._special_retrieve(button="left")

    @utils.toggle_clicklock
    def retrieve_with_lift(self) -> None:
        """Retreive the line, pause periodically."""
        logger.info("Retrieving with lift")
        self._special_retrieve(button="right")

    @utils.release_keys_after
    def _special_retrieve(self, button: str) -> None:
        if self.cfg.SELECTED.PRE_ACCELERATION:
            pag.keyDown("shift")
        i = RETRIEVAL_WITH_PAUSE_TIMEOUT
        while i > 0:
            utils.hold_mouse_button(self.cfg.SELECTED.RETRIEVE_DURATION, button)
            i = utils.sleep_and_decrease(i, self.cfg.SELECTED.RETRIEVE_DELAY)
            if self.detection.is_fish_hooked() or self.detection.is_retrieve_finished():
                return


    @utils.release_keys_after
    def pirk(self) -> None:
        """Start pirking until a fish is hooked.

        :param ctrl_enabled: whether to hold ctrl key during pirking
        :type ctrl_enabled: bool
        :raises TimeoutError: loop timed out
        """
        logger.info("Pirking")

        i = self.cfg.SELECTED.PIRK_TIMEOUT
        while i > 0:
            if self.detection.is_fish_hooked_twice():
                pag.click()
                return

            if self.cfg.SELECTED.PIRK_DURATION > 0:
                if self.cfg.SELECTED.CTRL:
                    pag.keyDown("ctrl")
                utils.hold_mouse_button(self.cfg.SELECTED.PIRK_DURATION, button="right")
                i = utils.sleep_and_decrease(i, self.cfg.SELECTED.PIRK_DELAY)
            else:
                i = utils.sleep_and_decrease(i, LOOP_DELAY)

        raise TimeoutError

    def elevate(self, drop: bool) -> None:
        """Perform elevator tactic (drop/rise) until a fish is hooked.

        :param drop: whether to drop or rise the lure
        :type drop: bool
        """
        logger.info("Dropping" if drop else "Rising")

        locked = True  # Reel is locked after tackle.sink()
        i = self.cfg.SELECTED.ELEVATE_TIMEOUT
        while i > 0:
            if self.detection.is_fish_hooked_twice():
                pag.click()
                return

            if self.cfg.SELECTED.DROP and drop:
                pag.press("enter")
                if locked:
                    delay = self.cfg.SELECTED.ELEVATE_DELAY
                else:
                    delay = self.cfg.SELECTED.ELEVATE_DURATION
                i = utils.sleep_and_decrease(i, delay)
            else:
                if locked:
                    i = utils.sleep_and_decrease(i, self.cfg.SELECTED.ELEVATE_DELAY)
                else:
                    utils.hold_mouse_button(self.cfg.SELECTED.ELEVATE_DURATION)
                    i -= self.cfg.SELECTED.ELEVATE_DURATION
            locked = not locked

        raise TimeoutError

    @_check_status
    def pull(self) -> None:
        logger.info("Pulling")
        self._pull()

    @utils.toggle_right_mouse_button
    @utils.toggle_clicklock
    def general_pull(self) -> None:
        """Pull the fish until it's captured.

        :raises exceptions.FishGotAwayError: fish got away during pulling
        :raises TimeoutError: loop timed out
        """
        i = PULL_TIMEOUT
        while i > 0:
            i = utils.sleep_and_decrease(i, LOOP_DELAY)
            if self.detection.is_fish_captured():
                return
            elif self.cfg.SCRIPT.SNAG_DETECTION and self.detection.is_line_snagged():
                raise exceptions.LineSnaggedError

        # Skip landing net if the retrieval is not finished yet
        if (self.cfg.SELECTED.MODE != "telescopic" and
            not self.detection.is_retrieve_finished()):
            return

        pag.press("space")
        sleep(LANDING_NET_DURATION)
        if self.detection.is_fish_captured():
            return
        pag.press("space")
        sleep(LANDING_NET_DELAY)

        if not self.detection.is_fish_hooked():
            raise exceptions.FishGotAwayError
        raise TimeoutError

    @utils.toggle_clicklock
    def telescopic_pull(self) -> None:
        """Pull the fish until it's captured, designed for telescopic rod.

        :raises TimeoutError: loop timed out
        """
        # check false postive first
        if not self.detection.is_fish_hooked():
            return

        # pull out landing net and check
        if not self.landing_net_out:
            pag.press("space")
            self.landing_net_out = True
        i = TELESCOPIC_RETRIEVAL_TIMEOUT
        while i > 0:
            i = utils.sleep_and_decrease(i, LOOP_DELAY)
            if self.detection.is_fish_captured():
                self.landing_net_out = False
                return
        raise TimeoutError()

    def switch_gear_ratio(self) -> None:
        """Switch the gear ratio of a conventional reel."""
        logger.info("Switching gear ratio")
        with pag.hold("ctrl"):
            pag.press("space")

    def move_mouse_randomly(self) -> None:
        """Randomly move the mouse for four times."""
        coords = []
        for _ in range(NUM_OF_MOVEMENT - 1):
            x, y = random.randint(-OFFSET, OFFSET), random.randint(-OFFSET, OFFSET)
            coords.append((x, y))
        coords.append((-sum(x for x, _ in coords), -sum(y for _, y in coords)))
        for x, y in coords:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y, 0, 0)
            sleep(ANIMATION_DELAY)


    def change_lure(self) -> None:
        logger.info("Changing lure")
        self._change_item_from_menu(item="lure")

    def change_dry_mix(self) -> None:
        logger.info("Changing dry mix")
        self._change_item_from_menu(item="dry_mix")

    def change_pva(self) -> None:
        logger.info("Changing PVA")
        self._change_item_from_menu(item="pva")

    def change_groundbait(self) -> None:
        logger.info("Changing groundbait")
        self._change_item_from_menu(item="groundbait")


    def _change_item_from_menu(self, item) -> None:
        logger.info("Searching item")
        menu_key = "h" if item == "pva" else "b"
        with pag.hold(menu_key):
            sleep(ANIMATION_DELAY)
            min_y = self.detection.get_baits_title_position()[1]
            candidates = list(self.detection.get_favorite_item_positions())
            if item == "lure":
                random.shuffle(candidates)
            replaced = False
            for candidate in candidates:
                # Check if the lure for replacement is already broken
                x, y = utils.get_box_center(candidate)
                if (item == "groundbait" and y < min_y or
                    item == "lure" and pag.pixel(x - 60, y + 190) == (178, 59, 30)):
                    continue

                pag.moveTo(x - 60, y + 190)
                pag.click()
                logger.info("Item changed successfully")
                replaced = True
                break

        if replaced:
            sleep(ANIMATION_DELAY)
            return

        logger.error("Failed to find an item to replace")
        if item == "pva":
            self.available = False # Skip casting