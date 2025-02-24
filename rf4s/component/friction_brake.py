"""
Module for friction brake related methods.
"""

import logging
from multiprocessing import Process, Value
from time import sleep, time

import pyautogui as pag

from rf4s.controller.detection import Detection

MAX_FRICTION_BRAKE = 30
UP = 1
DOWN = -1
FRICTION_BRAKE_MONITOR_DELAY = 2
LOOP_DELAY = 0.04

logger = logging.getLogger("rich")


class FrictionBrake:
    """Friction brake controller."""

    def __init__(self, cfg, lock, detection: Detection) -> None:
        self.cfg = cfg
        self.detection = detection
        self.cur = Value("i", cfg.FRICTION_BRAKE.INITIAL)
        self.lock = lock
        self.monitor_process = Process(target=monitor_friction_brake, args=(self,))

    def reset(
        self,
        target: int,
    ) -> None:
        """Reset to the target friction brake.

        :param target_friction_brake: target friction brake to reset
        :type target_friction_brake: int
        """
        logger.info("Resetting friction brake")
        for _ in range(MAX_FRICTION_BRAKE):
            pag.scroll(UP)

        diff = MAX_FRICTION_BRAKE - target
        for _ in range(abs(diff)):
            pag.scroll(DOWN)
        self.cur.value = target

    def change(self, increase: bool, bound: bool=True) -> None:
        """Increae or decrease friction.

        :param increase: increae or decreae the friction brake
        :type increase: bool
        """
        if increase:
            if not bound or self.cur.value < self.cfg.FRICTION_BRAKE.MAX:
                pag.scroll(UP, _pause=False)
                self.cur.value += 1
        else:
            if self.cur.value > 0:
                pag.scroll(DOWN, _pause=False)
                self.cur.value -= 1
        sleep(LOOP_DELAY)


def monitor_friction_brake(friction_brake: FrictionBrake, bound: bool=False):
    """Monitor friction brake bar and change it accordingly.

    This is used as target function in multiprocess.Process and must be pickable,
    thus it must be declared as a global function instead of a instance method.

    :param friction_brake: friction brake controller
    :type friction_brake: FrictionBrake
    :param bound: whether to check bounardies, defaults to False
    :type bound: bool, optional
    """
    logger.info("Monitoring friction brake")

    pre_time = time()
    fish_hooked = False

    try:
        while True:
            if not friction_brake.detection.is_fish_hooked_pixel():
                sleep(FRICTION_BRAKE_MONITOR_DELAY)
                fish_hooked = False
                continue
            elif not fish_hooked:
                sleep(friction_brake.cfg.FRICTION_BRAKE.START_DELAY)
                fish_hooked = True
            with friction_brake.lock:
                if friction_brake.detection.is_friction_brake_high():
                    friction_brake.change(increase=False, bound=bound)
                else:
                    cur_time = time()
                    if (
                        cur_time - pre_time
                        < friction_brake.cfg.FRICTION_BRAKE.INCREASE_DELAY
                    ):
                        continue
                    pre_time = cur_time
                    friction_brake.change(increase=True, bound=bound)
    except KeyboardInterrupt:
        pass
