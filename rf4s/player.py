"""
Module for Player class.
"""

import json
import logging
import os
import random
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from multiprocessing import Lock
# from email.mime.image import MIMEImage
from pathlib import Path
from time import sleep, time
from urllib import parse, request

import pyautogui as pag
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
from playsound import playsound
from rich import print
from rich.table import Table
from rich import box
from pynput import keyboard


from rf4s import exceptions, utils
from rf4s.component.friction_brake import FrictionBrake
from rf4s.component.tackle import Tackle
from rf4s.controller.detection import Detection
from rf4s.controller.timer import Timer
from rf4s.config import config
from rf4s.controller.window import Window

logger = logging.getLogger("rich")
random.seed(datetime.now().timestamp())

PRE_RETRIEVAL_DURATION = 0.5
PULL_OUT_DELAY = 3
DIG_DELAY = 5
DIG_TIMEOUT = 32
LOOP_DELAY = 2
ANIMATION_DELAY = 1
TICKET_EXPIRE_DELAY = 16
DISCONNECTED_DELAY = 8
WEAR_TEXT_UPDATE_DELAY = 2
BOUND = 2
PUT_DOWN_DELAY = 4

SCREENSHOT_DELAY = 2

TROLLING_KEY = "j"

FORWARD = "w"
LEFT_KEY = "a"
RIGHT_KEY = "d"


class Player:
    """Main interface of fishing loops and stages."""

    # pylint: disable=too-many-instance-attributes, disable=no-member
    # there are too many counters...
    # setting node's attributes will be merged on the fly

    def __init__(self, cfg, window: Window):
        """Initialize monitor, timer, timer and some trivial counters.

        :param setting: universal setting node, initialized in App()
        :type setting: Setting
        """
        self.cfg = cfg
        self.window = window
        self.timer = Timer(cfg)
        self.detection = Detection(cfg, window.supported)

        self.tackle_idx = 0
        if self.cfg.SELECTED.MODE == "bottom":
            self.num_tackle = len(self.cfg.KEY.BOTTOM_RODS)
        else:
            self.num_tackle = 1
        self.tackles = [
            Tackle(cfg, self.timer, self.detection)
            for _ in range(self.num_tackle)
        ]
        self.tackle = self.tackles[self.tackle_idx]

        self.friction_brake_lock = Lock()
        self.friction_brake = FrictionBrake(
            cfg, self.friction_brake_lock, self.detection
        )

        self.cast_miss_count = 0
        self.keep_fish_count = 0
        self.marked_count = 0
        self.unmarked_count = 0

        self.tea_count = 0
        self.carrot_count = 0
        self.alcohol_count = 0
        self.cur_coffee_count = 0
        self.total_coffee_count = 0
        self.harvest_count = 0

        self.have_new_lure = True
        self.have_new_groundbait = True
        self.have_new_dry_mix = True
        self.have_new_pva = True

    def start_fishing(self) -> None:
        """Start main fishing loop with specified fishing strategt."""
        if self.cfg.ARGS.FRICTION_BRAKE:
            logger.info("Spawing new process, do not quit the script")
            self.friction_brake.monitor_process.start()

        if (self.cfg.SELECTED.MODE not in ("telesopic", "bottom") and
            not self.detection.is_retrieve_finished()):
            logger.critical("The spool is not fully loaded with fishing line")
            sys.exit(1)

        logger.info("Starting fishing mode: '%s'", self.cfg.SELECTED.MODE)
        self._start_trolling()
        getattr(self, f"start_{self.cfg.SELECTED.MODE}_mode")()

    def _update_tackle(self) -> None:
        candidates = self._get_available_rods()
        if not candidates:
            self.general_quit("All rods are unavailable")
        if self.cfg.SCRIPT.RANDOM_ROD_SELECTION:
            self.tackle_idx = random.choice(candidates)
        else:
            self.tackle_idx = candidates[0]
        self.tackle = self.tackles[self.tackle_idx]

    def _get_available_rods(self) -> bool:
        if self.num_tackle == 1 and self.tackle.available:
            return [self.tackle]

        candidates = list(range(len(self.tackles)))
        # Rotate the candidates for sequential polling
        start = candidates.index(self.tackle_idx)
        candidates = candidates[start:] + candidates[:start]
        candidates = [i for i in candidates if self.tackles[i].available]

        #  Exclude current rod only if there's another available tackle
        if len(candidates) > 1 and self.tackle_idx in candidates:
            candidates.remove(self.tackle_idx)
        return candidates


    # ---------------------------------------------------------------------------- #
    #                              main fishing loops                              #
    # ---------------------------------------------------------------------------- #
    def start_spin_mode(self) -> None:
        """Main spin fishing loop for "spin" and "spin_with_pause"."""
        skip_cast = self.cfg.ARGS.SKIP_CAST
        while True:
            if not skip_cast:
                self._refill_stats()
                self._harvest_baits(pickup=True)
                self._reset_tackle()
                self._change_tackle_lure()
                self._cast_tackle()
            skip_cast = False

            if self.cfg.SELECTED.TYPE != "normal":
                utils.hold_mouse_button(self.cfg.SELECTED.TIGHTEN_DURATION)
                getattr(self.tackle, f"retrieve_with_{self.cfg.SELECTED.TYPE}")()
            self._retrieve_line()

            if self.detection.is_fish_hooked():
                self._pull_fish()
            else:
                self.cast_miss_count += 1

    def _change_tackle_lure(self) -> None:
        if not self.cfg.ARGS.LURE or not self.have_new_lure:
            return

        if self.timer.is_lure_changeable():
            logger.info("Changing lure randomly")
            try:
                self.tackle.equip_item("lure")
            except exceptions.ItemNotFoundError:
                logger.error("New lure not found")
                self.have_new_lure = False
        else:
            logger.info("Keep using the same lure")

    def _refill_pva(self) -> None:
        if not self.cfg.ARGS.PVA or not self.have_new_pva:
            return

        if self.detection.is_pva_chosen():
            logger.info("Pva is not used up yet")
        else:
            logger.info("Pva has been used up")
            try:
                self.tackle.equip_item("pva")
            except exceptions.ItemNotFoundError:
                logger.error("New pva not found")
                self.have_new_pva = False

    def _refill_dry_mix(self) -> None:
        if not self.cfg.ARGS.DRY_MIX or not self.have_new_dry_mix:
            return
        try:
            self.tackle.equip_item("dry_mix")
        except exceptions.ItemNotFoundError:
            logger.error("New dry mix not found")
            self.have_new_dry_mix = False

    def _refill_groundbait(self) -> None:
        if not self.cfg.ARGS.GROUNDBAIT or not self.have_new_groundbait:
            return

        if self.detection.is_groundbait_chosen():
            logger.info("Groundbait is not used up yet")
        else:
            try:
                self.tackle.equip_item("groundbait")
            except exceptions.ItemNotFoundError:
                logger.error("New groundbait not found")
                self.have_new_groundbait = False

    def start_bottom_mode(self) -> None:
        """Main bottom fishing loop."""
        check_miss_counts = [0] * self.num_tackle

        while True:
            if self.cfg.ARGS.SPOD_ROD and self.timer.is_spod_rod_castable():
                self._cast_spod_rod()
            self._refill_stats()
            self._harvest_baits()

            logger.info("Checking rod %s", self.tackle_idx + 1)
            pag.press(str(self.cfg.KEY.BOTTOM_RODS[self.tackle_idx]))
            sleep(ANIMATION_DELAY)
            if self.detection.is_fish_hooked():
                check_miss_counts[self.tackle_idx] = 0
                self._retrieve_line()
                self._pull_fish()
                self._reset_tackle()
                self._refill_groundbait()
                self._refill_pva()
                self._cast_tackle(lock=True)
            else:
                self._put_down_tackle(check_miss_counts)
            self._update_tackle()

    def start_pirk_mode(self) -> None:
        """Main marine fishing loop."""
        self._start_sink_mode(pirk=True)

    def start_elevator_mode(self) -> None:
        """Main marine fishing loop."""
        self._start_sink_mode(pirk=False)

    def _start_sink_mode(self, pirk: bool):
        perform_technique = self._do_pirking if pirk else self._do_elevating
        while True:
            if not self.cfg.ARGS.SKIP_CAST:
                self._refill_stats()
                self._reset_tackle()
                self._cast_tackle()
                self.tackle.sink()
            self.cfg.ARGS.SKIP_CAST = False

            perform_technique()
            self._retrieve_line()
            self._pull_fish()

    def start_telescopic_mode(self) -> None:
        self._start_float_mode(telescopic=True)

    def start_bolognese_mode(self) -> None:
        """Main bolognese fishing loop."""
        self._start_float_mode(telescopic=False)

    def _start_float_mode(self, telescopic) -> None:
        """Main float fishing loop."""
        monitor, hold_mouse_button = self._get_controllers(telescopic)

        while True:
            self._refill_stats()
            self._harvest_baits(pickup=True)
            self._reset_tackle()
            self._cast_tackle()

            try:
                monitor()
            except TimeoutError:
                self.cast_miss_count += 1
                continue

            sleep(self.cfg.SELECTED.PULL_DELAY)
            hold_mouse_button(PRE_RETRIEVAL_DURATION)
            self._pull_fish()

    def _get_controllers(self, telescopic):
        if telescopic:
            hold_mouse_button = utils.hold_mouse_button
            monitor = self._monitor_float_state
        else:
            if self.detection.is_clip_open():
                logger.warning("Clip is not set, fall back to camera mode")
                monitor = self._monitor_float_state
            else:
                monitor = self._monitor_clip_state
            hold_mouse_button = utils.hold_mouse_buttons

        return monitor, hold_mouse_button


    def _monitor_clip_state(self) -> None:
        """Monitor the state of the bolognese."""
        i = self.cfg.SELECTED.DRIFT_TIMEOUT
        while i > 0:
            i = utils.sleep_and_decrease(i, self.cfg.SELECTED.CHECK_DELAY)
            if self.detection.is_clip_open():
                return

        raise TimeoutError

    # this is not done yet :(
    # def trolling_fishing(self) -> None:
    #     # temp
    #     rod_idx = -1
    #     rod_count = len(self.bottom_rods_shortcuts) #!
    #     base_waiting_time = 16

    #     while True:
    #         self.refilling_stage()
    #         self.harvesting_stage()
    #         # if there is a rod on hand
    #         if rod_count == 3:
    #             sleep(base_waiting_time)
    #             logger.info(f'Checking rod {3}')
    #             self.retrieving_stage()
    #             if monitor.is_fish_hooked():
    #                 self.pulling_stage()
    #             else:
    #                 self.resetting_stage()

    #         for rod_key in self.bottom_rods_shortcuts[:-1]:
    #             pag.press(rod_key)
    #             if monitor.is_fish_hooked():
    #                 self.retrieving_stage()
    #                 if monitor.is_fish_hooked():
    #                     self.pulling_stage()
    #                     self.tackle.cast(self.cast_power_level)
    #                 else:
    #                     self.cast_miss_count += 1

    #         # if both missed, recast the third rod
    #         self.tackle.cast(self.cast_power_level)

    # ---------------------------------------------------------------------------- #
    #            stages and their helper functions in main fishing loops           #
    # ---------------------------------------------------------------------------- #

    def _harvest_baits(self, pickup=False) -> None:
        """Harvest the bait."""
        if not self.cfg.ARGS.HARVEST or not self.detection.is_energy_high():
            return
        logger.info("Harvesting baits")
        self._access_item("digging_tool")
        sleep(PULL_OUT_DELAY)
        pag.click()

        i = DIG_TIMEOUT
        while i > 0:
            i = utils.sleep_and_decrease(i, DIG_DELAY)
            if self.detection.is_harvest_success():
                pag.press("space")
                pag.press("backspace")
                sleep(ANIMATION_DELAY)
                self.harvest_count += 1
                break

        if pickup:
            self._access_item("main_rod")
            sleep(ANIMATION_DELAY)

        # When timed out, do not raise a TimeoutError but defer it to resetting stage

    def _refill_stats(self) -> None:
        """Refill player stats using tea and carrot."""
        if not self.cfg.ARGS.REFILL:
            return

        logger.info("Refilling player stats")
        # Comfort is affected by weather, add a check to avoid over drink
        if self.detection.is_comfort_low() and self.timer.is_tea_drinkable():
            self._access_item("tea")
            self.tea_count += 1
            sleep(ANIMATION_DELAY)

        if self.detection.is_hunger_low():
            self._access_item("carrot")
            self.carrot_count += 1
            sleep(ANIMATION_DELAY)

    def _drink_alcohol(self) -> None:
        """Drink alcohol with given quantity."""
        if not self.cfg.ARGS.ALCOHOL or not self.timer.is_alcohol_drinkable():
            return

        logger.info("Drinking alcohol")
        for _ in range(self.cfg.STAT.ALCOHOL_PER_DRINK):
            self._access_item("alcohol")
            sleep(ANIMATION_DELAY)
        self.alcohol_count += self.cfg.STAT.ALCOHOL_PER_DRINK

    def _drink_coffee(self) -> None:
        """Drink coffee."""
        if not self.cfg.ARGS.COFFEE or self.detection.is_energy_high():
            return

        if self.cur_coffee_count > self.cfg.STAT.COFFEE_LIMIT:
            pag.press("esc")  # Just back to control panel to reduce power usage
            self._handle_termination("Coffee limit reached", shutdown=False)

        logger.info("Drinking coffee")
        for _ in range(self.cfg.COFFEE_PER_DRINK):
            self._access_item("coffee")
            sleep(ANIMATION_DELAY)
        self.cur_coffee_count += self.cfg.COFFEE_PER_DRINK
        self.total_coffee_count += self.cfg.COFFEE_PER_DRINK


    def _access_item(self, item: str) -> None:
        """Access item by name using quick selection shortcut or menu.

        :param item: the name of the item
        :type item: str
        """
        key = str(self.cfg.KEY[item.upper()])
        if key != "-1":
            pag.press(key)
            return

        # Open food menu
        with pag.hold("t"):
            sleep(ANIMATION_DELAY)
            food_position = self.detection.get_food_position(item)
            pag.moveTo(food_position)
            pag.click()

    @utils.reset_friction_brake_after
    def _reset_tackle(self) -> None:
        """Reset the tackle till it's ready."""
        sleep(ANIMATION_DELAY)
        if self.detection.is_tackle_ready():
            return

        if self.detection.is_lure_broken():
            self._handle_broken_lure()
            return

        if not self.detection.is_groundbait_chosen():
            self._refill_dry_mix()
            return

        if not self.detection.is_bait_chosen():
            if len(self.tackles) == 1:
                self.general_quit("Run out of bait")
            self.tackle.available = False
            return

        while True:
            try:
                self.tackle.reset()
                return
            except exceptions.FishHookedError:
                self._pull_fish()
                return
            except exceptions.FishCapturedError:
                self._handle_fish()
                return
            except exceptions.LineAtEndError:
                self.general_quit("Fishing line is at its end")
            except exceptions.LineSnaggedError:
                self._handle_snagged_line()
            except TimeoutError:  # rare events
                self._handle_timeout()


    def _handle_snagged_line(self):
        if len(self.tackles):
            self.general_quit("Line is snagged")
        self.tackle.available = False

    def _cast_spod_rod(self):
        self._access_item("spod_rod")
        sleep(ANIMATION_DELAY)
        self._reset_tackle()

        # If no dry mix is available, skip casting
        if not self.tackle.available:
            self.tackle.available = True
            return
        self._cast_tackle(lock=True, update=False)
        pag.press("0")
        sleep(ANIMATION_DELAY)

    def _cast_tackle(self, lock=False, update=True):
        if self.cfg.ARGS.PAUSE and self.timer.is_script_pausable():
            self._pause_script()

        if self.cfg.ARGS.BITE:
            self.window.save_screenshot(self.timer.get_cur_timestamp())
        self.tackle.cast(lock)
        if update:
            self.timer.update_cast_time()

    def _pause_script(self):
        pag.press("esc")
        bound = self.cfg.PAUSE.DURATION // 20
        offset = random.randint(-bound, bound)
        sleep(self.cfg.PAUSE.DURATION + offset)
        pag.press("esc")

    def _handle_timeout(self) -> None:
        """Handle common timeout events."""
        if self.detection.is_tackle_broken():
            self.general_quit("Tackle is broken")

        if self.detection.is_disconnected():
            self.disconnected_quit()

        if self.detection.is_ticket_expired():
            self._handle_expired_ticket()

    def _handle_broken_lure(self):
        """Handle the broken lure event according to the settings."""
        match self.cfg.ARGS.BROKEN_LURE:
            case "replace":
                self._replace_broken_lures()
            case "alarm":
                playsound(str(Path(self.cfg.SCRIPT.ALARM_SOUND).resolve()))
                self.window.activate_script_window()
                print("Please replace your lure")
                print(input("Press enter to continue..."))
                self.window.activate_game_window()
            case _:
                self.general_quit("Broken lure auto-replace is disabled")

    @utils.release_keys_after
    def _handle_termination(self, msg: str, shutdown: bool) -> None:
        """Send email and plot diagram, quit the game if necessary

        :param msg: quit message
        :type msg:
        :param shutdown: whether to shutdown the computer or not
        :type shutdown: bool
        """
        result = self.gen_result(msg)
        if self.cfg.ARGS.EMAIL:
            self.send_email(result)
        if self.cfg.ARGS.MIAOTIXING:
            self.send_miaotixing(result)
        if self.cfg.ARGS.PLOT:
            self.plot_and_save()
        if shutdown and self.cfg.ARGS.SHUTDOWN:
            os.system("shutdown /s /t 5")
        print(result)
        sys.exit()

    def _retrieve_line(self) -> None:
        """Retrieve the line till it's fully retrieved with timeout handling."""
        if self.detection.is_retrieve_finished():
            return

        first = True
        gr_switched = False
        self.cur_coffee_count = 0
        while True:
            try:
                self.tackle.retrieve(first)
                break
            except exceptions.FishCapturedError:
                self._handle_fish()
                break
            except exceptions.LineAtEndError:
                self.general_quit("Fishing line is at its end")
            except exceptions.LineSnaggedError:
                self._handle_snagged_line()
            except TimeoutError:
                self._handle_timeout()
                first = False
                if self.cfg.ARGS.GEAR_RATIO and not gr_switched:
                    self.tackle.switch_gear_ratio()
                    gr_switched = True
                pag.keyUp("shift")
                self._drink_coffee()

        pag.keyUp("shift")
        if gr_switched:
            self.tackle.switch_gear_ratio()

    def _do_pirking(self) -> None:
        """Perform pirking till a fish hooked with timeout handling."""
        while True:
            try:
                self.tackle.pirk()
                break
            except TimeoutError:
                self._handle_timeout()
                if self.cfg.SELECTED.ADJUST:
                    logger.info("Adjusting lure depth")
                    pag.press("enter")  # Open reel
                    sleep(self.cfg.SELECTED.DEPTH_ADJUST_DELAY)
                    utils.hold_mouse_button(self.cfg.SELECTED_TIGHTEN_DURATION)
                else:
                    self._reset_tackle()
                    self._cast_tackle()
                    self.tackle.sink()
                self.cast_miss_count += 1

    def _do_elevating(self) -> None:
        """Perform elevating till a fish hooked with timeout handling."""
        drop = False
        while True:
            try:
                drop = not drop
                self.tackle.elevate(drop)
                break
            except TimeoutError:
                self._handle_timeout()
                self.cast_miss_count += 1
                # lazy skip

    def _monitor_float_state(self) -> None:
        """Monitor the state of the float."""
        logger.info("Monitoring float state")
        reference_img = pag.screenshot(region=self.detection.float_camera_rect)
        i = self.cfg.SELECTED.DRIFT_TIMEOUT
        while i > 0:
            i = utils.sleep_and_decrease(i, self.cfg.SELECTED.CHECK_DELAY)
            if self.detection.is_float_state_changed(reference_img):
                logger.info("Float status changed")
                return

        raise TimeoutError

    def _pull_fish(self) -> None:
        """Pull the fish up, then handle it."""
        if not self.detection.is_fish_hooked():
            return

        self._drink_alcohol()
        while True:
            try:
                self.tackle.pull()
                self._handle_fish()
                return
            except exceptions.FishGotAwayError:
                return
            except exceptions.LineSnaggedError:
                self._handle_snagged_line()
            except TimeoutError:
                self._handle_timeout()
                if self.cfg.SELECTED.MODE == "float":
                    sleep(PUT_DOWN_DELAY)
                    continue
                self._retrieve_line()

    def _handle_fish(self) -> None:
        """Keep or release the fish and record the fish count.

        !! a trophy ruffe will break the checking mechanism?
        """
        if not self.detection.is_fish_captured():
            return
        logger.info("Handling fish")
        if self.cfg.ARGS.SCREENSHOT:
            self.window.save_screenshot(self.timer.get_cur_timestamp())

        if self.detection.is_fish_marked():
            self.marked_count += 1
        else:
            self.unmarked_count += 1
            if self.cfg.ARGS.MARKED and not self._is_fish_whitelisted():
                pag.press("backspace")
                return

        # Fish is marked, unmarked release is disabled, or fish is in whitelist
        sleep(self.cfg.KEEPNET.DELAY)
        pag.press("space")

        self.keep_fish_count += 1
        limit = self.cfg.KEEPNET.CAPACITY - self.cfg.ARGS.FISHES_IN_KEEPNET
        if self.keep_fish_count == limit:
            self._handle_full_keepnet()

        # Avoid wrong cast hour
        if self.cfg.SELECTED.MODE in ["bottom", "pirk", "elevator"]:
            self.timer.update_cast_time()
        self.timer.add_cast_time()

    def _handle_full_keepnet(self):
        msg = "Keepnet is full"
        match self.cfg.KEEPNET.FULL_ACTION:
            case "alarm":
                playsound(str(Path(self.cfg.SCRIPT.ALARM_SOUND).resolve()))
                self.window.activate_script_window()
                print(input("Press enter to continue..."))
                self.window.activate_game_window()
                with keyboard.Listener(on_release=self._on_release) as listner:
                    listner.join()
                logger.info("Continue running script")
            case "quit":
                self.general_quit(msg)
            case _:
                raise ValueError

    def _on_release(self, _: keyboard.KeyCode) -> None:
        sys.exit()

    def _is_fish_whitelisted(self):
        if self.cfg.KEEPNET.RELEASE_WHITELIST is None:
            return False

        for species in self.cfg.KEEPNET.RELEASE_WHITELIST:
            if self.detection.is_fish_species_matched(species):
                return True
        return False

    # ---------------------------------------------------------------------------- #
    #                                     misc                                     #
    # ---------------------------------------------------------------------------- #

    def general_quit(self, msg: str) -> None:
        """Quit the game through control panel.

        :param msg: the cause of the termination
        :type msg: str
        """
        logger.critical(msg)
        sleep(ANIMATION_DELAY)
        pag.press("esc")
        # pag.click()  # Avoid possible ClickLock stuck
        sleep(ANIMATION_DELAY)
        pag.moveTo(self.detection.get_quit_position())
        pag.click()
        sleep(ANIMATION_DELAY)
        pag.moveTo(self.detection.get_yes_position())
        pag.click()

        self._handle_termination(msg, shutdown=True)

    def disconnected_quit(self) -> None:
        """Quit the game through main menu."""
        pag.click()  # Avoid possible ClickLock stuck
        pag.press("space")
        # Sleep to bypass the black screen (experimental)
        sleep(DISCONNECTED_DELAY)

        pag.press("space")
        sleep(ANIMATION_DELAY)

        pag.moveTo(self.detection.get_exit_icon_position())
        pag.click()
        sleep(ANIMATION_DELAY)
        pag.moveTo(self.detection.get_confirm_exit_icon_position())
        pag.click()

        self._handle_termination("Game disconnected", shutdown=True)

    def gen_result(self, msg: str):
        #TODO
        fish_count_total = self.marked_count + self.unmarked_count
        cast_count = self.cast_miss_count + fish_count_total

        if fish_count_total == 0:
            marked_ratio = 0
        else:
            marked_ratio = int(self.marked_count / fish_count_total * 100)
        mum_desc = f"{self.marked_count} / {self.unmarked_count} / {marked_ratio}%"

        bite_ratio = int(fish_count_total / cast_count * 100) if cast_count != 0 else 0
        hmb_desc = f"{fish_count_total} / {cast_count} / {bite_ratio}%"

        results = (
            ("Cause of termination", msg),
            ("Start time", self.timer.get_start_datetime()),
            ("Finish time", self.timer.get_cur_datetime()),
            ("Running time", self.timer.get_running_time()),
            ("Fish caught", self.keep_fish_count),
            ("Marked / Unmarked / Mark ratio", mum_desc),
            ("Hit / Miss / Bite ratio", hmb_desc),
            ("Alcohol consumed", self.alcohol_count),
            ("Coffee consumed", self.total_coffee_count),
            ("Tea consumed", self.tea_count),
            ("Carrot consumed", self.carrot_count),
            ("Harvest baits count", self.harvest_count),
        )
        self.results = results

        table = Table(
            "Field",
            "Value",
            title="Running Results",
            box = box.DOUBLE,
            show_header=False
        )

        for k, v in results:
            table.add_row(k, str(v))
        return table

    def send_email(self, table) -> None:
        """Send a notification email to the user's email address."""
        sender = self.cfg.NOTIFICATION.EMAIL
        password = self.cfg.NOTIFICATION.PASSWORD
        smtp_server = self.cfg.NOTIFICATION.SMTP_SERVER

        msg = MIMEMultipart()
        msg["Subject"] = "RussianFishing4Script: Notice of Program Termination"
        msg["From"] = sender
        recipients = [sender]
        msg["To"] = ", ".join(recipients)

        results = ""
        for k, v in self.results:
            results += f"{k}: {v}\n"
        msg.attach(MIMEText(results))

        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            # smtp_server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        logger.info("Email sent successfully")

    def send_miaotixing(self, table) -> None:
        """Send a notification Message to the user's miaotixing service."""

        # Prepare the data to be sent as query parameters
        data_dict = self.results

        miao_code = self.cfg.NOTIFICATION.MIAO_CODE

        # Customizable Text Prompt Message
        text = (
            "Cause of termination:"
            + data_dict["Cause of termination"]
            + "\nStart time:"
            + data_dict["Start time"]
            + "\nFinish time:"
            + data_dict["Finish time"]
            + "\nRunning time:"
            + data_dict["Running time"]
            + "\nFish caught:"
            + str(data_dict["Fish caught"])
            + "\nMarked / Unmarked / Mark ratio:"
            + data_dict["Marked / Unmarked / Mark ratio"]
            + "\nHit / Miss / Bite ratio:"
            + data_dict["Hit / Miss / Bite ratio"]
            + "\nAlcohol consumed:"
            + str(data_dict["Alcohol consumed"])
            + "\nCoffee consumed:"
            + str(data_dict["Coffee consumed"])
            + "\nTea consumed:"
            + str(data_dict["Tea consumed"])
            + "\nCarrot consumed:"
            + str(data_dict["Carrot consumed"])
            + "\nHarvest baits count:"
            + str(data_dict["Harvest baits count"])
        )

        url = "http://miaotixing.com/trigger?" + parse.urlencode(
            {"id": miao_code, "text": text, "type": "json"}
        )

        with request.urlopen(url) as page:
            result = page.read()
            json_object = json.loads(result)
            if json_object["code"] == 0:
                print("A notification message to the user's miaotixing service.")
            else:
                print(
                    "Sending failed with error code:"
                    + str(json_object["code"])
                    + ", Description:"
                    + json_object["msg"]
                )

    def plot_and_save(self) -> None:
        """Plot and save an image using rhour and ghour list from timer object."""
        if self.keep_fish_count == 0:
            return

        cast_rhour_list, cast_ghour_list = self.timer.get_cast_time_list()
        _, ax = plt.subplots(nrows=1, ncols=2)
        # _.canvas.manager.set_window_title('Record')
        ax[0].set_ylabel("Fish")

        last_rhour = cast_rhour_list[-1]  # Hour: 0, 1, 2, 3, 4, "5"
        fish_per_rhour = [0] * (last_rhour + 1)  # Idx: (0, 1, 2, 3, 4, 5) = 6
        for hour in cast_rhour_list:
            fish_per_rhour[hour] += 1
        ax[0].plot(range(last_rhour + 1), fish_per_rhour)
        ax[0].set_title("Fish Caughted per Real Hour")
        ax[0].set_xticks(range(last_rhour + 2))
        ax[0].set_xlabel("Hour (real running time)")
        ax[0].yaxis.set_major_locator(MaxNLocator(integer=True))

        fish_per_ghour = [0] * 24
        for hour in cast_ghour_list:
            fish_per_ghour[hour] += 1
        ax[1].bar(range(0, 24), fish_per_ghour)
        ax[1].set_title("Fish Caughted per Game Hour")
        ax[1].set_xticks(range(0, 24, 2))
        ax[1].set_xlabel("Hour (game time)")
        ax[1].yaxis.set_major_locator(MaxNLocator(integer=True))

        # plt.tight_layout()
        plt.savefig(f"../logs/{self.timer.get_cur_timestamp()}.png")
        print("The Plot has been saved under logs/")

    def _handle_expired_ticket(self):
        """Select and use the ticket according to boat_ticket_duration argument."""
        if self.cfg.ARGS.BOAT_TICKET is None:
            pag.press("esc")
            sleep(TICKET_EXPIRE_DELAY)
            self.general_quit("Boat ticket expired")

        logger.info("Renewing boat ticket")
        ticket_loc = self.detection.get_ticket_position(self.cfg.ARGS.BOAT_TICKET)
        if ticket_loc is None:
            pag.press("esc")  # Close ticket menu
            sleep(ANIMATION_DELAY)
            self.general_quit("Boat ticket not found")
        pag.moveTo(ticket_loc)
        pag.click(clicks=2, interval=0.1)  # pag.doubleClick() not implemented
        sleep(ANIMATION_DELAY)

    def _replace_broken_lures(self):
        """Replace multiple broken items (lures)."""
        logger.info("Replacing broken lures")
        pag.press("v")
        sleep(ANIMATION_DELAY)

        scrollbar_position = self.detection.get_scrollbar_position()
        if scrollbar_position is None:
            logger.info("Scroll bar not found, changing lures for normal rig")
            while self._open_broken_lure_menu():
                self._replace_item(lure=True)
            pag.press("v")
            return

        logger.info("Scroll bar found, changing lures for dropshot rig")
        pag.moveTo(scrollbar_position)
        for _ in range(5):
            sleep(ANIMATION_DELAY)
            pag.drag(xOffset=0, yOffset=125, duration=0.5, button="left")

            replaced = False
            while self._open_broken_lure_menu():
                self._replace_item(lure=True)
                replaced = True

            if replaced:
                pag.moveTo(self.detection.get_scrollbar_position())
        pag.press("v")
        sleep(ANIMATION_DELAY)

    def _open_broken_lure_menu(self) -> bool:
        """Search for text of broken item, open selection menu if found.

        :return: True if broken item is found, False otherwise
        :rtype: bool
        """
        logger.info("Searching for broken lure")
        broken_item_position = self.detection.get_100wear_position()
        if broken_item_position is None:
            logger.warning("Broken lure not found")
            return False

        # click item to open selection menu
        pag.moveTo(broken_item_position)
        sleep(ANIMATION_DELAY)
        pag.click()
        sleep(ANIMATION_DELAY)
        return True

    def _replace_item(self, lure: bool) -> None:
        """Select a favorite item for replacement and replace the broken one."""
        logger.info("Searching for favorite items")
        favorite_item_positions = self.detection.get_favorite_item_positions()
        while True:
            favorite_item_position = next(favorite_item_positions, None)
            if favorite_item_position is None:
                # TODO: different tackle?
                msg = "Favorite item not found"
                logger.critical(msg)
                sys.exit(1)
                # pag.press("esc")
                # sleep(ANIMATION_DELAY)
                # pag.press("esc")
                # sleep(ANIMATION_DELAY)
                # self.general_quit(msg)

            # Check if the lure for replacement is already broken
            x, y = utils.get_box_center(favorite_item_position)
            if pag.pixel(x - 60, y + 190) != (178, 59, 30):  # Magic value
                logger.info("Item has been replaced")
                pag.moveTo(x - 60, y + 190)
                pag.click(clicks=2, interval=0.1)
                sleep(WEAR_TEXT_UPDATE_DELAY)
                break

            logger.warning("Favorite item found but not available")

    def _put_down_tackle(self, check_miss_counts: list[int]) -> None:
        """Update counters, put down the tackle and wait for a while.

        :param check_miss_counts: miss counts of all rods
        :type check_miss_counts: list[int]
        :param rod_idx: current index of the rod
        :type rod_idx: int
        """
        self.cast_miss_count += 1
        check_miss_counts[self.tackle_idx] += 1
        if check_miss_counts[self.tackle_idx] >= self.cfg.SELECTED.CHECK_MISS_LIMIT:
            check_miss_counts[self.tackle_idx] = 0
            self._reset_tackle()
            self._refill_groundbait()
            self._refill_pva()
            self._cast_tackle(lock=True)

        pag.press("0")
        random_offset = random.uniform(-BOUND, BOUND)
        sleep(self.cfg.SELECTED.CHECK_DELAY + random_offset)


    def _start_trolling(self):
        """Start trolling and change moving direction based on trolling setting.

        Available options: never, forward, left, right.
        """
        if self.cfg.ARGS.TROLLING is None:
            return
        logger.info("Starting trolling")
        print(self.cfg.ARGS.TROLLING)
        # pag.press(TROLLING_KEY)
        pag.keyDown("w")
        if self.cfg.ARGS.TROLLING not in ("left", "right"): # Forward
            return
        pag.keyDown(LEFT_KEY if self.cfg.ARGS.TROLLING == "left" else RIGHT_KEY)



    def test(self):
        """Boo!"""
        while True:
            sleep(0.1)
            print(self.detection.is_pva_chosen())
            print(self.detection.is_groundbait_chosen())
            print(self.detection.is_bait_chosen())

            # print(self.detection.get_groundbait_slot_position())
