"""
Module for pyautogui.locateOnScreen and pag.pixel wrappers.
"""

# pylint: disable=missing-function-docstring
# docstring for every functions? u serious?

import logging
import sys
import time
from pathlib import Path

import pyautogui as pag
from pyscreeze import Box

from rf4s.controller.window import Window

logger = logging.getLogger("rich")

CRITICAL_COLOR = (206, 56, 21)
WARNING_COLOR = (227, 149, 23)
WHITE = (255, 255, 255)

MIN_GRAY_SCALE_LEVEL = 150
YELLOW_FRICTION_BRAKE = (200, 214, 63)
ORANGE_FRICTION_BRAKE = (229, 188, 0)
RED_FRICTION_BRAKE = (206, 56, 21)
COLOR_TOLERANCE = 64

ROOT = Path(__file__).resolve().parents[2]


# ------------------------ Friction brake coordinates ------------------------ #
# ----------------------------- 900p - 1080p - 2k ---------------------------- #
# ------ left - red - yellow - center(left + 424) - yellow - red - right ----- #
# "bases": ((480, 270), (320, 180), (0, 0))
# "absolute": {"x": (855, 960, 1066, 1279, 1491, 1598, 1702, "y": (1146, 1236, 1412)}
# "1600x900": {"x": (375, 480, 586, 799, 1011, 1118, 1222), "y": 876},
# "1920x1080": {"x": (535, 640, 746, 959, 1171, 1278, 1382), "y": 1056},
# "2560x1440": {"x": (855, 960, 1066, 1279, 1491, 1598, 1702), "y": 1412},

# snag: x + 15, y
# spool: x + 15, y + 15

# For friction brake bar, check the left point only
COORD_OFFSETS = {
    "1600x900": {
        "friction_brake_very_high": (502, 799, 1096),
        "friction_brake_high": (459, 799, 1139),
        "friction_brake_medium": (417, 799, 1181),
        "friction_brake_low": (396, 799, 1202),
        "fish_icon": (389, 844),
        "clip_icon": (1042, 844),
        "spool_icon": (1077, 844),
        "snag_icon": (1147, 829),
        "float_camera": (720, 654),
    },
    "1920x1080": {
        "friction_brake_very_high": (662, 959, 1256),
        "friction_brake_high": (619, 959, 1299),
        "friction_brake_medium": (577, 959, 1341),
        "friction_brake_low": (556, 959, 1362),
        "fish_icon": (549, 1024),
        "clip_icon": (1202, 1024),
        "spool_icon": (1237, 1024),
        "snag_icon": (1307, 1009),
        "float_camera": (880, 834),
    },
    "2560x1440": {
        "friction_brake_very_high": (982, 1279, 1576),
        "friction_brake_high": (939, 1279, 1619),
        "friction_brake_medium": (897, 1279, 1661),
        "friction_brake_low": (876, 1279, 1682),
        "fish_icon": (869, 1384),
        "clip_icon": (1522, 1384),
        "spool_icon": (1557, 1384),
        "snag_icon": (1627, 1369),
        "float_camera": (1200, 1194),
    },
}

CAMERA_OFFSET = 40
SIDE_LENGTH = 160
SIDE_LENGTH_HALF = 80


class Detection:
    """A class that holds different aliases of locateOnScreen(image)."""

    # pylint: disable=too-many-public-methods

    def __init__(self, cfg, window_is_supported):
        """Initialize setting.

        :param setting: general setting node
        :type setting: Setting
        """
        self.cfg = cfg
        self.window_box = Window().get_box()
        self.image_dir = ROOT / "static" / cfg.SCRIPT.LANGUAGE

        if window_is_supported:
            self._set_absolute_coords()

    def _get_image_box(self, image: str, confidence: float, multiple: bool=False) -> Box | None:
        """A wrapper for locateOnScreen method and path resolving.

        :param image: base name of the image
        :type image: str
        :param confidence: matching confidence for locateOnScreen
        :type confidence: float
        :return: image box, None if not found
        :rtype: Box
        """
        image_path = str(self.image_dir / f"{image}.png")
        if multiple:
            return pag.locateAllOnScreen(image_path, confidence=confidence)
        return pag.locateOnScreen(image_path, confidence=confidence)

    def _set_absolute_coords(self) -> None:
        """Add offsets to the base coordinates to get absolute ones."""
        window_size = f"{self.window_box[2]}x{self.window_box[3]}"
        self.coord_offsets = COORD_OFFSETS[window_size]

        for key, value in self.coord_offsets.items():
            setattr(self, f"{key}_coord", self._get_absolute_coord(key))

        # self.fish_icon_coord = self._get_absolute_coord("fish_icon")
        # self.spool_icon_coord = self._get_absolute_coord("spool_icon")
        # self.snag_icon_coord = self._get_absolute_coord("snag_icon")
        # self.clip_icon_coord = self._get_absolute_coord("clip_icon")
        friction_brake_key = f"friction_brake_{self.cfg.FRICTION_BRAKE.SENSITIVITY}"
        self.friction_brake_coord = self._get_absolute_coord(friction_brake_key)

        bases = self._get_absolute_coord("float_camera")
        if self.cfg.SELECTED.MODE in ("telescopic", "bolognese"):
            match self.cfg.SELECTED.CAMERA_SHAPE:
                case "tall":
                    bases[0] += CAMERA_OFFSET
                    width, height = SIDE_LENGTH_HALF, SIDE_LENGTH
                case "wide":
                    bases[1] += CAMERA_OFFSET
                    width, height = SIDE_LENGTH, SIDE_LENGTH_HALF
                case "square":
                    width, height = SIDE_LENGTH, SIDE_LENGTH
                case _:
                    logger.critical(
                        "Invalid camera shape: '%s'",
                        self.cfg.SELECTED.CAMERA_SHAPE
                    )
                    sys.exit(1)
            self.float_camera_rect = (*bases, width, height)  # (left, top, w, h)

    def _get_absolute_coord(self, offset_key: str) -> list[int]:
        """Calculate absolute coordinate based on given key.

        :param offset_key: a key in offset dictionary
        :type offset_key: str
        :return: converted absolute coordinate
        :rtype: list[int]
        """
        return [
            self.window_box[0] + self.coord_offsets[offset_key][0],
            self.window_box[1] + self.coord_offsets[offset_key][1],
        ]

    # ------------------------ unmarked release whitelist ------------------------ #
    def is_fish_species_matched(self, species: str) -> Box | None:
        """Check if the captured fish match the given species.

        :param species: mackerel, saithe, herring, squid, scallop, or mussel
        :type species: str
        :return: image box, None if not found
        :rtype: Box
        """
        return self._get_image_box(species, 0.9)

    # ----------------------------- unmarked release ----------------------------- #
    def is_fish_marked(self):
        return self._get_image_box("mark", 0.7)

    def is_fish_yellow_marked(self):
        return self._get_image_box("trophy", 0.7)

    # -------------------------------- fish status ------------------------------- #
    def is_fish_hooked(self):
        return self._get_image_box("get", 0.9)

    def is_fish_hooked_twice(self) -> bool:
        if not self.is_fish_hooked():
            return False

        # check if the fish got away after a short delay
        time.sleep(self.cfg.SELECTED.HOOK_DELAY)
        if self.is_fish_hooked():
            return True
        return False

    def is_fish_captured(self):
        return self._get_image_box("keep", 0.9)

    # ---------------------------- retrieval detection --------------------------- #
    def is_retrieve_finished(self):
        if self.cfg.ARGS.RAINBOW_LINE:
            return self._is_rainbow_line_0or5m()
        return self._is_spool_full()

    def _is_rainbow_line_0or5m(self):
        return self._get_image_box(
            "5m", self.cfg.SCRIPT.SPOOL_CONFIDENCE
        ) or self._get_image_box(
            "0m", self.cfg.SCRIPT.SPOOL_CONFIDENCE
        )

    def _is_spool_full(self):
        return self._get_image_box(
            "wheel", self.cfg.SCRIPT.SPOOL_CONFIDENCE
        )

    # ------------------------------ hint detection ------------------------------ #
    def is_tackle_ready(self):
        return self._get_image_box("ready", 0.6)

    def is_tackle_broken(self):
        return self._get_image_box("broke", 0.6)

    def is_lure_broken(self):
        return self._get_image_box("lure_is_broken", 0.7)

    def is_moving_in_bottom_layer(self):
        return self._get_image_box("movement", 0.7)

    # ------------------------------ hint detection ------------------------------ #
    def is_disconnected(self):
        return self._get_image_box("disconnected", 0.9)

    def is_ticket_expired(self):
        return self._get_image_box("ticket", 0.9)

    # ------------------------------- item crafting ------------------------------ #
    def is_operation_failed(self):
        return self._get_image_box("warning", 0.8)

    def is_operation_success(self):
        return (self._get_image_box("ok_black", 0.8) or
                self._get_image_box("ok_white", 0.8))

    def is_material_complete(self):
        return not self._get_image_box("material_slot", 0.9)

    # ---------------------- quiting game from control panel --------------------- #
    def get_quit_position(self):
        return self._get_image_box("quit", 0.8)

    def get_yes_position(self):
        return self._get_image_box("yes", 0.8)

    def get_make_position(self):
        return self._get_image_box("make", 0.9)

    # ------------------------ quiting game from main menu ----------------------- #
    def get_exit_icon_position(self):
        return self._get_image_box("exit", 0.8)

    def get_confirm_exit_icon_position(self):
        return self._get_image_box("confirm_exit", 0.8)

    # ----------------------------- baits harvesting ----------------------------- #
    def is_harvest_success(self):
        return self._get_image_box("harvest_confirm", 0.8)

    # ----------------------------- player stat icon ----------------------------- #
    def _get_energy_icon_position(self):
        box = self._get_image_box("energy", 0.8)
        return box if box is None else pag.center(box)

    def _get_food_icon_position(self):
        box = self._get_image_box("food", 0.8)
        return box if box is None else pag.center(box)

    def _get_comfort_icon_position(self):
        box = self._get_image_box("comfort", 0.8)
        return box if box is None else pag.center(box)

    # -------------------------- player stat refill item ------------------------- #
    def get_food_position(self, food: str) -> Box | None:
        """Get the position of food in quick selection menu.

        :param food: carrot, tea, or coffee
        :type food: str
        :return: image box, None if not found
        :rtype: Box
        """
        return self._get_image_box(food, 0.8)

    def get_ticket_position(self, duration: int) -> Box | None:
        """Locate the image of boat ticket according to the given duration.

        :param duration: duration of boat ticket
        :type duration: int
        :return: image box, None if not found
        :rtype: Box
        """
        return self._get_image_box(f"ticket_{duration}", 0.95)

    # -------------------------- broken lure replacement ------------------------- #
    def get_scrollbar_position(self):
        return self._get_image_box("scrollbar", 0.97)

    def get_100wear_position(self):
        return self._get_image_box("100wear", 0.98)

    def get_favorite_item_positions(self):
        # TODO
        return self._get_image_box("favorite", 0.95, multiple=True)

    # ---------------------------------------------------------------------------- #
    #                               image analyzation                              #
    # ---------------------------------------------------------------------------- #
    def is_energy_high(self) -> bool:
        """Check if the energy level is high enough to harvest baits

        :return: True if high enough, False otherwise
        :rtype: bool
        """
        pos = self._get_energy_icon_position()
        if not pos:
            return False
        x, y = int(pos.x), int(pos.y)
        # default threshold: 0.74,  well done FishSoft
        last_point = int(19 + 152 * self.cfg.STAT.ENERGY_THRESHOLD) - 1
        return pag.pixel(x + 19, y) == pag.pixel(x + last_point, y)

    def is_hunger_low(self) -> bool:
        """Check if hunger is low.

        :return: True if low, False otherwise
        :rtype: bool
        """
        pos = self._get_food_icon_position()
        if not pos:
            return False
        x, y = int(pos.x), int(pos.y)
        last_point = int(18 + 152 * self.cfg.STAT.HUNGER_THRESHOLD) - 1
        return not pag.pixel(x + 18, y) == pag.pixel(x + last_point, y)

    def is_comfort_low(self) -> bool:
        """Check if comfort is low.

        :return: True if low, False otherwise
        :rtype: bool
        """
        pos = self._get_comfort_icon_position()
        if not pos:
            return False
        x, y = int(pos.x), int(pos.y)
        last_point = int(18 + 152 * self.cfg.STAT.COMFORT_THRESHOLD) - 1
        return not pag.pixel(x + 18, y) == pag.pixel(x + last_point, y)

    def is_line_snagged(self) -> bool:
        """Check the top of the snag icon to see if the line is snagged.

        :return: True if snagged, False otherwise
        :rtype: bool
        """
        return pag.pixel(*self.snag_icon_coord) == CRITICAL_COLOR

    def is_line_at_end(self):
        return pag.pixel(*self.spool_icon_coord) in (WARNING_COLOR, CRITICAL_COLOR)

    def is_friction_brake_high(self) -> bool:
        """Check if the friction brake is too high using friction brake bar center.

        :return: True if pixel color matched, False otherwise
        :rtype: bool
        """
        return pag.pixelMatchesColor(
            *self.friction_brake_coord, RED_FRICTION_BRAKE, COLOR_TOLERANCE
        )

    def is_fish_hooked_pixel(self) -> bool:
        return all(
            c > MIN_GRAY_SCALE_LEVEL
            for c in pag.pixel(*self.fish_icon_coord)
        )

    def is_float_state_changed(self, reference_img):
        current_img = pag.screenshot(region=self.float_camera_rect)
        return not pag.locate(
            current_img,
            reference_img,
            grayscale=True,
            confidence=self.cfg.SELECTED.FLOAT_SENSITIVITY,
        )

    def is_clip_open(self) -> bool:
        return not all(
            c > MIN_GRAY_SCALE_LEVEL
            for c in pag.pixel(*self.clip_icon_coord)
        )

    def is_pva_chosen(self):
        # return pag.pixel(*self.pva_icon_coord) != WHITE
        return self._get_image_box("pva_icon", 0.6) is None

    def is_groundbait_chosen(self):
        return self._get_image_box("groundbait_icon", 0.6) is None

    def is_bait_chosen(self):
        return self._get_image_box("bait_icon", 0.6) is None


    def get_groundbait_position(self):
        return self._get_image_box("classic_feed_mix", 0.95)

    def get_dry_mix_position(self):
        return self._get_image_box("dry_feed_mix", 0.95)
