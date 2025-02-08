"""
Main CLI.

Usage: app.py
"""

# pylint: disable=no-member
# setting node's attributes will be merged on the fly

import logging
import os
import shlex
import signal
import smtplib
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from socket import gaierror

import pyautogui as pag
from dotenv import load_dotenv
from prettytable import PrettyTable
from pynput import keyboard

import script
from player import Player
from setting import COMMON_CONFIGS, SPECIAL_CONFIGS, Setting

from yacs.config import CfgNode as CN
from config.config import setup_cfg, dict_to_cfg

format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=logging.INFO, format=format, datefmt=datefmt)
logger = logging.getLogger(__name__)

# ------------------------- flag name 1, help message ------------------------ #
HELP = (
    ("c", "drink coffee if retrieval takes longer than 2 minutes"),
    ("A", "regularly drink alcohol before keeping the fish"),
    ("r", "refill hunger and comfort by consuming tea and carrot"),
    ("H", "harvest baits before casting, support mode: bottom, spin, and float"),
    ("g", "switch the gear ratio after the retrieval timed out"),
    ("P", "save a chart of catch logs in logs/"),
    ("s", "shutdown computer after terminated without user interruption"),
    ("l", "lift the tackle constantly while pulling a fish"),
    ("e", "send email to yourself after terminated without user interruption"),
    ("M", "send miaotixing notification after terminated without user interruption"),
    ("S", "take screenshots of every fish you catch and save them in screenshots/"),
    ("C", "skip rod casting for the first fish, support mode: spin, marine, wakey_rig"),
    ("f", "change friction brake automatically"),
    ("o", "recast the spod rod automatically"),
    ("L", "change current lure with a random one automatically"),
    ("x", "move mouse randomly before casting the rod"),
    ("X", "pause the script after catchig a fish regularly"),
    ("b", "take a screenshot when a fish bites and save it in screenshots/"),
)

# ----------------- flag name 2, attribute name, description ----------------- #
COMMON_ARGS = (
    ("coffee", "coffee_drinking_enabled", "Coffee drinking"),
    ("alcohol", "alcohol_drinking_enabled", "Alcohol drinking"),
    ("refill", "player_stat_refill_enabled", "Player stat refill"),
    ("harvest", "baits_harvesting_enabled", "Baits harvesting"),
    ("gear_ratio", "gr_switching_enabled", "Gear ratio switching"),
    ("plot", "plotting_enabled", "Plotting"),
    ("shutdown", "shutdown_enabled", "Shutdown"),
    ("lift", "lifting_enabled", "Lifting"),
    ("email", "email_sending_enabled", "Email sending"),
    ("miaotixing", "miaotixing_sending_enabled", "miaotixing sending"),
    ("result_screenshot", "result_screenshot_enabled", "Result screenshot"),
    ("cast", "cast_skipping_enabled", "Cast skipping"),
    ("friction_brake", "friction_brake_changing_enabled", "Friction brake changing"),
    ("spod_rod", "spod_rod_recast_enabled", "Spod rod recast"),
    ("lure", "lure_changing_enabled", "Lure changing"),
    ("mouse", "mouse_moving_enabled", "Mouse moving"),
    ("pause", "pause_enabled", "Pause"),
    ("bite_screenshot", "bite_screenshot_enabled", "Bite screenshot"),
)

# ----------------- flag name 2, attribute name, description ----------------- #
SPECIAL_ARGS = (
    ("marked", "unmarked_release_enabled", "Unmarked release"),
    ("rainbow_line", "rainbow_line_enabled", "Rainbow line"),
    ("fishes_in_keepnet", "fishes_in_keepnet", "Fishes in keepnet"),
    ("boat_ticket_duration", "boat_ticket_duration", "Boat ticket duratioin"),
)

ASCII_LOGO = """
██████╗ ███████╗██╗  ██╗███████╗
██╔══██╗██╔════╝██║  ██║██╔════╝
██████╔╝█████╗  ███████║███████╗
██╔══██╗██╔══╝  ╚════██║╚════██║
██║  ██║██║          ██║███████║
╚═╝  ╚═╝╚═╝          ╚═╝╚══════╝"""
# https://patorjk.com/software/taag/#p=testall&f=3D-ASCII&t=RF4S%0A, ANSI Shadow

ROOT = Path(__file__).resolve().parents[1]

class App:
    """Main application class."""

    def __init__(self):
        """Merge args into setting node."""
        self.pid = None
        self.player = None
        self.table = None

        self.cfg = setup_cfg()
        self.cfg.merge_from_file(ROOT / "config.yaml")

        # Parser will use the last occurence if the arguments are duplicated,
        # so put argv at the end to overwrite launch options.
        args_list = shlex.split(self.cfg.SCRIPT.LAUNCH_OPTIONS) + sys.argv[1:]
        args = self._setup_parser().parse_args(args_list)
        if not self._is_args_valid(args):
            sys.exit(1)
        args_cfg = CN()
        args_cfg["ARGS"] = dict_to_cfg(vars(args)) # Avoid naming confliction
        self.cfg.merge_from_other_cfg(args_cfg)

        if not self._is_smtp_valid() or not self._is_images_valid():
            sys.exit(1)
        self.cfg.freeze()

    def _setup_parser(self) -> ArgumentParser:
        """Configure argparser."""
        parser = ArgumentParser(description="Start AFK script for Russian Fishing 4")

        for arg_help, common_arg in zip(HELP, COMMON_ARGS):
            flag1 = f"-{arg_help[0]}"
            flag2 = f"--{common_arg[0]}"
            help_msg = arg_help[1]
            parser.add_argument(flag1, flag2, action="store_true", help=help_msg)

        # ----------------------------- release strategy ----------------------------- #
        release_strategy = parser.add_mutually_exclusive_group()
        release_strategy.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="Keep all captured fishes, used by default",
        )
        release_strategy.add_argument(
            "-m", "--marked", action="store_true", help="Keep only the marked fishes"
        )

        # ----------------------- retrieval detection strategy ----------------------- #
        retrieval_detecton_strategy = parser.add_mutually_exclusive_group()
        retrieval_detecton_strategy.add_argument(
            "-d",
            "--default-spool",
            action="store_true",
            help="Use default spool icon for retrieval detection, used by default",
        )
        retrieval_detecton_strategy.add_argument(
            "-R",
            "--rainbow-line",
            action="store_true",
            help="Use rainbow line meter for retrieval detection",
        )

        # -------------------------- arguments with metavar -------------------------- #
        profile_selection_strategy = parser.add_mutually_exclusive_group()
        profile_selection_strategy.add_argument(
            "-p",
            "--pid",
            metavar="PID",
            type=int,
            help="Id of the profile you want to use",
        )
        profile_selection_strategy.add_argument(
            "-N",
            "--pname",
            metavar="PROFILE_NAME",
            type=str,
            help="Name of the profile you want to use",
        )
        parser.add_argument(
            "-n",
            "--fishes_in_keepnet",
            metavar="FISH_COUNT",
            type=int,
            default=0,
            help="Number of fishes in your keepnet, 0 if not specified",
        )
        parser.add_argument(
            "-t",
            "--boat_ticket_duration",
            metavar="DURATION",
            type=int,
            choices=[1, 2, 3, 5],
            help=(
                "Enable boat ticket auto renewal, "
                "use 1, 2, 3, or 5 to speicfy the ticket duration"
            ),
        )

        return parser

    def _is_args_valid(self, args: Namespace) -> bool:
        if not 0 <= args.fishes_in_keepnet < self.cfg.SCRIPT.KEEPNET_CAPACITY:
            logger.critical(
                "Invalid number of fishes in keepnet: '%s'",
                args.fishes_in_keepnet
            )
            return False

        if args.pid is not None and not self._is_pid_valid(str(args.pid)):
            logger.critical("Invalid profile id: '%s'", args.pid)
            return False

        if args.pname is not None and args.pname not in self.cfg.PROFILE:
            logger.critical("Invalid profile name: '%s'", args.pname)
            return False

        # boat_ticket_duration already checked by choices[...]

        return True

    def _is_pid_valid(self, pid: str) -> bool:
        """Validate the profile id."""
        return pid.isdigit() and 0 <= int(pid) < len(self.cfg.PROFILE)

    def _is_smtp_valid(self) -> None:
        """Validate email configuration in .env."""
        if not self.cfg.ARGS.EMAIL or not self.cfg.SCRIPT.SMTP_VERIFICATION:
            return True

        logger.debug("Verifying SMTP connection...")

        load_dotenv()
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD")
        smtp_server_name = os.getenv("SMTP_SERVER")

        if not smtp_server_name:
            logger.critical("SMTP_SERVER is not specified")
            return False

        try:
            with smtplib.SMTP_SSL(smtp_server_name, 465) as smtp_server:
                smtp_server.login(email, password)
        except smtplib.SMTPAuthenticationError:
            logger.critical("Email address or password not accepted")
            print(
                (
                    "Please configure your email address and password in .env\n"
                    "If Gmail is used, please refer to "
                    "https://support.google.com/accounts/answer/185833 \n"
                    "to get more information about app password authentication"
                )
            )
            return False
        except (TimeoutError, gaierror):
            logger.critical("Invalid SMTP Server or connection timed out")
            return False
        return True

    def _is_images_valid(self) -> None:
        """Verify the file integrity of static/{language}.

        Compare files in static/en and static/{language}
        and print missing files in static/{language}.
        """
        if not self.cfg.SCRIPT.IMAGE_VERIFICATION:
            return True

        logger.debug("Verifying image files...")
        if self.cfg.SCRIPT.LANGUAGE == "en":
            return True

        image_dir = ROOT / "static" / self.cfg.SCRIPT.LANGUAGE
        try:
            current_images = [f for f in image_dir.iterdir() if f.is_file()]
        except FileNotFoundError:
            logger.critical("Invalid language: '%s'", self.cfg.SCRIPT.LANGUAGE)
            return False
        template_dir = ROOT / "static" / "en"
        target_images = [f for f in template_dir.iterdir() if f.is_file()]
        missing_images = set(target_images) - set(current_images)
        if len(missing_images) > 0:
            logger.critical("Integrity check failed")
            table = PrettyTable(header=False, align="l", title="Missing Images")
            for filename in missing_images:
                table.add_row([filename])
            print(table)
            return False

    def display_available_profiles(self) -> None:
        """List available user profiles from setting node."""
        table = PrettyTable(header=False, align="l")
        table.title = "Welcome! Select a profile to start"
        for i, profile in enumerate(self.cfg.PROFILE):
            table.add_row([f"{i:>2}. {profile}"])
        print(table)

    def ask_for_pid(self) -> None:
        """Get and validate user profile id from user input."""
        print("Enter profile id to use it, q to exit.")
        pid = input(">>> ")
        while not self._is_pid_valid(pid):
            if pid.strip() == "q":
                sys.exit()
            print("Invalid profile id, please try again.")
            pid = input(">>> ")
        self.pid = int(pid)

    def on_release(self, key: keyboard.KeyCode) -> None:
        """Callback for button release.

        :param key: key code used by OS
        :type key: keyboard.KeyCode
        """
        if key == keyboard.KeyCode.from_char(self.setting.quitting_shortcut):
            os.kill(os.getpid(), signal.CTRL_C_EVENT)
            sys.exit()


if __name__ == "__main__":
    print(ASCII_LOGO)
    print("https://github.com/dereklee0310/RussianFishing4Script")
    app = App()
    if app.pid is None:
        app.display_available_profiles()
        app.ask_for_pid()
    app.player = Player(app.cfg)
    print(app.cfg) # cfg.dump() doesn't preserve order, but idgaf

    #TODO: Update coords and Window()
    if script.verify_window_size(app.setting):
        app.setting.set_absolute_coords()
    app.setting.window_controller.activate_game_window()

    if app.cfg.KEY.QUIT != "CTRL-C":
        listener = keyboard.Listener(on_release=app.on_release)
        listener.start()

    try:
        app.player.start_fishing()
    except KeyboardInterrupt:
        pass

    # app.player.friction_brake_monitor_process.join()
    print(app.player.gen_result("Terminated by user"))
    if app.setting.plotting_enabled:
        app.player.plot_and_save()

    # CTRL_C_EVENT: https://stackoverflow.com/questions/58455684/
