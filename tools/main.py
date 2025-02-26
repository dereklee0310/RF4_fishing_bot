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

from pynput import keyboard
from rich.logging import RichHandler
from rich import print, box
from rich.panel import Panel
from rich.table import Table, Column
from rich.console import Console
from rich.text import Text

sys.path.append(".") # python -m module -> python file

from yacs.config import CfgNode as CN

from rf4s.config import config
from rf4s.controller.window import Window
from rf4s.player import Player

# Ignore %(name)s because it's verbose
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")
# Reference: https://rich.readthedocs.io/en/latest/logging.html

ARGUMENTS = (
    ("c", "coffee", "drink coffee if stamina is low"),
    ("A", "alcohol", "drink alcohol before keeping the fish regularly"),
    ("r", "refill", "refill hunger and comfort by consuming tea and carrot"),
    ("H", "harvest", "harvest baits before casting"),
    ("g", "gear_ratio", "switch the gear ratio after the retrieval timed out"),
    ("f", "friction_brake", "enable auto friction brake"),
    ("l", "lift", "lift the tackle constantly while pulling a fish"),
    ("C", "skip_cast", "skip to retrieving for the first fish, mode: spin, marine"), # TODO
    ("o", "spod_rod", "recast spod rod regularly"),
    ("L", "lure", "change current lure with a random one regularly"),
    ("x", "mouse", "move mouse randomly before casting the rod"),
    ("X", "pause", "pause the script before casting the rod regularly"),
    ("b", "bite", "take a screenshot after casting in screenshots/ (for fish spot)"),
    ("S", "screenshot", "take a screenshot of every fish you caught in screenshots/"),
    ("e", "email", "send email noticication afterward"),
    ("P", "plot", "save fishing data in /logs"),
    ("M", "miaotixing", "send miaotixing notification afterward"),
    ("s", "shutdown", "shutdown computer afterward"),
    ("gb", "groundbait", "enable groundbait refill, mode: bottom"),
    ("dm", "dry_mix", "enable dry mix refill, mode: bottom"),
    ("pva", "pva", "enable pva refill, mode: bottom"),
)

LOGO = """
██████╗ ███████╗██╗  ██╗███████╗
██╔══██╗██╔════╝██║  ██║██╔════╝
██████╔╝█████╗  ███████║███████╗
██╔══██╗██╔══╝  ╚════██║╚════██║
██║  ██║██║          ██║███████║
╚═╝  ╚═╝╚═╝          ╚═╝╚══════╝"""
LINK = "https://github.com/dereklee0310/RussianFishing4Script"
# https://patorjk.com/software/taag/#p=testall&f=3D-ASCII&t=RF4S%0A, ANSI Shadow

ROOT = Path(__file__).resolve().parents[1]

class App:
    """Main application class."""

    def __init__(self):
        """Merge args into setting node."""
        print(Panel.fit(LOGO, box=box.HEAVY))
        print(LINK)
        self.cfg = config.setup_cfg()
        self.cfg.merge_from_file(ROOT / "config.yaml")

        # Parser will use the last occurence if the arguments are duplicated,
        # so put argv at the end to overwrite launch options.
        args_list = shlex.split(self.cfg.SCRIPT.LAUNCH_OPTIONS) + sys.argv[1:]
        args = self._setup_parser().parse_args(args_list)
        if not self._is_args_valid(args):
            sys.exit(1)

        args_cfg = CN({"ARGS": config.dict_to_cfg(vars(args))})
        self.cfg.merge_from_other_cfg(args_cfg)
        if not self._is_smtp_valid() or not self._is_images_valid():
            sys.exit(1)

        self.args = args
        self.console = Console()

    def _setup_parser(self) -> ArgumentParser:
        """Configure argparser."""
        parser = ArgumentParser(description="Start AFK script for Russian Fishing 4")
        parser.add_argument("opts", nargs="*", help="modify config options using the command-line")


        for argument in ARGUMENTS:
            flag1 = f"-{argument[0]}"
            flag2 = f"--{argument[1]}"
            help = argument[2]
            parser.add_argument(flag1, flag2, action="store_true", help=help)

        # ----------------------------- release strategy ----------------------------- #
        release_strategy = parser.add_mutually_exclusive_group()
        release_strategy.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="keep all captured fishes, used by default",
        )
        release_strategy.add_argument(
            "-m", "--marked", action="store_true", help="keep only the marked fishes"
        )

        # ----------------------- retrieval detection strategy ----------------------- #
        retrieval_detecton_strategy = parser.add_mutually_exclusive_group()
        retrieval_detecton_strategy.add_argument(
            "-d",
            "--default-spool",
            action="store_true",
            help="use default spool icon for retrieval detection, used by default",
        )
        retrieval_detecton_strategy.add_argument(
            "-R",
            "--rainbow-line",
            action="store_true",
            help="use rainbow line meter for retrieval detection",
        )

        # -------------------------- arguments with metavar -------------------------- #
        profile_selection_strategy = parser.add_mutually_exclusive_group()
        profile_selection_strategy.add_argument(
            "-p",
            "--pid",
            type=int,
            help="id of the profile you want to use",
            metavar="PID",
        )
        profile_selection_strategy.add_argument(
            "-N",
            "--pname",
            type=str,
            help="name of the profile you want to use",
            metavar="PROFILE_NAME",
        )

        parser.add_argument(
            "-n",
            "--fishes-in-keepnet",
            default=0,
            type=int,
            help="number of fishes in your keepnet, 0 by default",
            metavar="FISH_COUNT",
        )
        parser.add_argument(
            "-t",
            "--boat-ticket",
            nargs="?",
            const=5,
            type=int,
            choices=[1, 2, 3, 5],
            help=(
                "enable boat ticket auto renewal, DURATION: '1', '2', '3' or '5', "
                "will use a 5 hour ticket if duration is not specified"
            ),
            metavar="DURATION",
        )

        parser.add_argument(
            "-T",
            "--trolling",
            nargs="?",
            const="forward",
            type=str,
            choices=["forward", "left", "right"],
            help=("enable trolling mode, DIRECTION: 'forward',''left', or 'right', "
                  "will only move forward by press 'j' if direction is not specified"),
            metavar="DIRECTION",
        )

        parser.add_argument(
            "-bl",
            "--broken-lure",
            nargs="?",
            const="replace",
            type=str,
            choices=["replace", "alarm"],
            help=(
                "enable broken lure auto-replace, ACTION: 'replace' or 'alarm', "
                "will replace the broken lure if action is not specified"
            ), # TODO
            metavar="ACTION",
        )
        return parser

    def _is_args_valid(self, args: Namespace) -> bool:
        if not 0 <= args.fishes_in_keepnet < self.cfg.KEEPNET.CAPACITY:
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

        logger.info("Verifying SMTP connection...")

        email = self.cfg.NOTIFICATION.EMAIL
        password = self.cfg.NOTIFICATION.PASSWORD
        smtp_server_name = self.cfg.NOTIFICATION.SMTP_SERVER

        if self.cfg.NOTIFICATION.SMTP_SERVER == "smtp.example.com":
            logger.critical("SMTP_SERVER is not specified")
            return False

        try:
            with smtplib.SMTP_SSL(smtp_server_name, 465) as smtp_server:
                smtp_server.login(email, password)
        except smtplib.SMTPAuthenticationError:
            logger.critical("Email address or app password not accepted")
            print(
                (
                    "Please check your email address and password.\n"
                    "If Gmail is used, please refer to "
                    "https://support.google.com/accounts/answer/185833 \n"
                    "to get more information about app password authentication."
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

        logger.info("Verifying image files...")
        if self.cfg.SCRIPT.LANGUAGE == "en":
            return True

        image_dir = ROOT / "static" / self.cfg.SCRIPT.LANGUAGE
        try:
            current_images = [f.name for f in image_dir.iterdir() if f.is_file()]
        except FileNotFoundError:
            logger.critical("Invalid language: '%s'", self.cfg.SCRIPT.LANGUAGE)
            return False
        template_dir = ROOT / "static" / "en"
        target_images = [f.name for f in template_dir.iterdir() if f.is_file()]
        missing_images = set(target_images) - set(current_images)
        if len(missing_images) > 0:
            logger.critical("Integrity check failed")
            from rich.style import Style
            table = Table(
                # "Filename",
                Column("Filename", style=Style(color="red")),
                title="Missing Images",
                box=box.DOUBLE,
                show_header=False
            )
            for filename in missing_images:
                table.add_row(f"static/{self.cfg.SCRIPT.LANGUAGE}/{filename}")
            print(table)
            return False

    def _is_profile_valid(self, profile_name):
        if profile_name not in self.cfg.PROFILE:
            logger.critical("Invalid profile name: '%s'", profile_name)
            return False

        mode = self.cfg.PROFILE[profile_name].MODE
        if mode.upper() not in self.cfg.PROFILE:
            logger.critical("Invalid mode: '%s'", mode)
            return False

        expected_keys = set(self.cfg.PROFILE[mode.upper()])
        actual_keys = set(self.cfg.PROFILE[profile_name])

        invalid_keys = actual_keys - expected_keys
        missing_keys = expected_keys - actual_keys

        if invalid_keys or missing_keys:
            for key in invalid_keys:
                logger.critical("Invalid setting: '%s'", key)
            for key in missing_keys:
                logger.critical("Missing setting: '%s'", key)
            return False
        return True

    def _display_available_profiles(self) -> None:
        """List available user profiles from setting node."""
        table = Table(
            "Profile",
            title="Select a profile to start :rocket:",
            show_header=False,
            min_width=36,
        )
        for i, profile in enumerate(self.cfg.PROFILE):
            table.add_row(f"{i:>2}. {profile}")
        print(table)

    def _get_pid(self) -> None:
        """Get and validate user profile id from user input."""
        print("Enter profile id to use, q to exit:")

        while True:
            pid = input(">>> ")
            if self._is_pid_valid(pid):
                break
            if pid == "q":
                sys.exit()
            self._print_error("Invalid profile id, please try again.")

        self.cfg.ARGS.PID = int(pid)

    def _print_error(self, msg):
        text = Text(msg)
        text.stylize("red")
        self.console.print(text)

    def _setup_user_profile(self):
        if self.cfg.ARGS.PNAME is not None:
            profile_name = self.cfg.ARGS.PNAME
        else:
            if self.cfg.ARGS.PID is None:
                self._display_available_profiles()
                self._get_pid()
            profile_name = list(self.cfg.PROFILE)[self.cfg.ARGS.PID]

        if not self._is_profile_valid(profile_name):
            sys.exit(1)

        self.cfg.SELECTED = CN({"NAME": profile_name})
        self.cfg.SELECTED.set_new_allowed(True)
        self.cfg.SELECTED.merge_from_other_cfg(self.cfg.PROFILE[profile_name])

        # Merge args.opts here because we can only overwrite cfg.SELECTED
        # after it's constructed using profile id or name.
        # Process list-like values if possible
        if "KEY.BOTTOM_RODS" in self.args.opts:
            value_idx = self.args.opts.index("KEY.BOTTOM_RODS") + 1
            self.args.opts[value_idx] = [
                x.strip() for x in self.args.opts[value_idx].split(",")
            ]
        self.cfg.merge_from_list(self.args.opts)
        config.print_cfg(self.cfg.SELECTED)


    def setup_window(self):
        self.window = Window()
        width, height = self.window.get_box()[2:]
        if self.window.title_bar_exist:
            logger.info("Window mode detected. Please don't move the game window")
        if not self.window.supported:
            logger.warning(
                "Invalid window size '%s', use '2560x1440', '1920x1080' or '1600x900'",
                f"{width}x{height}",
            )
            logger.warning('Window mode must be "Borderless windowed" or "Window mode"')
            logger.error("Snag detection will be disabled")
            logger.error("Spooling detection will be disabled")
            logger.error("Auto friction brake will be disabled")

        self.cfg.ARGS.FRICTION_BRAKE = False
        self.cfg.SCRIPT.SNAG_DETECTION = False
        self.cfg.SCRIPT.SPOOLING_DETECTION = False

        if self.cfg.SELECTED.MODE in ("telescopic", "bolognese"):
            logger.critical(
                "Fishing mode '%s' doesn't support window size '%s'",
                self.cfg.SELECTED.MODE,
                f"{width}x{height}"
            )
            sys.exit(1)

    def _setup_player(self):
        self.player = Player(self.cfg, self.window)

    def _on_release(self, key: keyboard.KeyCode) -> None:
        """Callback for button release.

        :param key: key code used by OS
        :type key: keyboard.KeyCode
        """
        if key == keyboard.KeyCode.from_char(self.cfg.KEY.QUIT):
            os.kill(os.getpid(), signal.CTRL_C_EVENT)
            sys.exit()

    def start(self):
        self._setup_user_profile()
        self.setup_window()
        self._setup_player()
        self.cfg.freeze()
        self.window.activate_game_window()

        if self.cfg.KEY.QUIT != "CTRL-C":
            listener = keyboard.Listener(on_release=self._on_release)
            listener.start()

        # self.player.test()

        try:
            self.player.start_fishing()
        except KeyboardInterrupt:
            pass

        # self.player.friction_brake_monitor_process.join()
        print(self.player.gen_result("Terminated by user"))
        if self.cfg.ARGS.PLOT:
            self.player.plot_and_save()



if __name__ == "__main__":
    app = App()
    app.start()

    # CTRL_C_EVENT: https://stackoverflow.com/questions/58455684/
