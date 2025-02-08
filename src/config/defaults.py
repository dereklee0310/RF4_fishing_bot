"""Default yacs config node."""

from yacs.config import CfgNode as CN

_C = CN()
_C.VERSION = 1.0

_C.SCRIPT = CN()
_C.SCRIPT.LANGUAGE = "en"
_C.SCRIPT.LAUNCH_OPTIONS = ""
_C.SCRIPT.SMTP_VERIFICATION = True
_C.SCRIPT.IMAGE_VERIFICATION = True
_C.SCRIPT.KEEPNET_CAPACITY = 100
_C.SCRIPT.SPOOL_CONFIDENCE = 0.985
_C.SCRIPT.KEEP_FISH_DELAY = 1.0
_C.SCRIPT.SNAG_DETECTION = True
_C.SCRIPT.RANDOM_ROD_SELECTION = True
_C.SCRIPT.SPOD_ROD_RECAST_DELAY = 1800 # 30 minutes
_C.SCRIPT.LURE_CHANGE_DELAY = 1800 # 30 minutes
_C.SCRIPT.KEEPNET_FULL_ACTION = "quit"
_C.SCRIPT.ALARM_SOUND = "../static/sound/guitar.wav"
_C.SCRIPT.RELEASE_WHITELIST = ("mackerel", "saithe", "herring", "squid", "scallop", "mussel")


_C.KEY = CN()
_C.KEY.TEA = -1
_C.KEY.CARROT = -1
_C.KEY.RODS = (1, 2, 3)
_C.KEY.COFFEE = 4
_C.KEY.DIGGING_TOOL = 5
_C.KEY.ALCOHOL = 6
_C.KEY.MAIN_ROD = 1
_C.KEY.SPOD_ROD = 7
_C.KEY.QUIT = "CTRL-C"


_C.STAT = CN()
_C.STAT.ENERGY_THRESHOLD = 0.74
_C.STAT.HUNGER_THRESHOLD = 0.5
_C.STAT.COMFORT_THRESHOLD = 0.51
_C.STAT.COFFEE_LIMIT = 10
_C.STAT.COFFEE_PER_DRINK = 1
_C.STAT.ALCOHOL_DELAY = 900 # 15 minutes
_C.STAT.ALCOHOL_PER_DRINK = 1


_C.FRICTION_BRAKE = CN()
_C.FRICTION_BRAKE.INITIAL = 29
_C.FRICTION_BRAKE.MAX = 30
_C.FRICTION_BRAKE.START_DELAY = 2.0
_C.FRICTION_BRAKE.INCREASE_DELAY = 1.0


_C.PAUSE = CN()
_C.PAUSE.DELAY = 1800 # 30 minutes
_C.PAUSE.DURATION = 600 # 10 minutes

_C.PROFILE = CN()
# ---------------------------------------------------------------------------- #
#                             Spin Fishing Profile                             #
# ---------------------------------------------------------------------------- #
_C.PROFILE.SPIN = CN()
_C.PROFILE.SPIN.MODE = "spin"
_C.PROFILE.SPIN.CAST_POWER_LEVEL = 5.0
_C.PROFILE.SPIN.CAST_DELAY = 6.0
_C.PROFILE.SPIN.TIGHTENING_DURATION = 1.0
_C.PROFILE.SPIN.RETRIEVE_DURATION = 1.1
_C.PROFILE.SPIN.RETRIEVE_DELAY = 3.0
_C.PROFILE.SPIN.PRE_ACCELERATION = False
_C.PROFILE.SPIN.POST_ACCELERATION = "off"


# ---------------------------------------------------------------------------- #
#                            Bottom Fishing Profile                            #
# ---------------------------------------------------------------------------- #
_C.PROFILE.BOTTOM = CN()
_C.PROFILE.BOTTOM.MODE = "bottom"
_C.PROFILE.BOTTOM.CAST_POWER_LEVEL = 5.0
_C.PROFILE.BOTTOM.CAST_DELAY = 4.0
_C.PROFILE.BOTTOM.ACCELERATION = "off"
_C.PROFILE.BOTTOM.CHECK_DELAY = 32.0


# ---------------------------------------------------------------------------- #
#                      Marine / Wakey Rig Pirking Profile                      #
# ---------------------------------------------------------------------------- #
_C.PROFILE.PIRK = CN()
_C.PROFILE.PIRK.MODE = "pirk"
_C.PROFILE.PIRK.CAST_POWER_LEVEL = 1.0
_C.PROFILE.PIRK.CAST_DELAY = 4.0
_C.PROFILE.PIRK.SINK_TIMEOUT = 60.0
_C.PROFILE.PIRK.TIGHTEN_DURATION = 1.0
_C.PROFILE.PIRK.PIRK_DURATION = 0.5
_C.PROFILE.PIRK.PIRK_DELAY = 2.0
_C.PROFILE.PIRK.PIRK_TIMEOUT = 32.0
_C.PROFILE.PIRK.PIRK_TIMEOUT_ACTION = "adjust"
_C.PROFILE.PIRK.ACCELERATION = "auto"
_C.PROFILE.PIRK.HOOK_DELAY = 0.0
_C.PROFILE.PIRK.TROLLING = "off"


# ---------------------------------------------------------------------------- #
#                            Marine Elevator Profile                           #
# ---------------------------------------------------------------------------- #
_C.PROFILE.ELEVATOR = CN()
_C.PROFILE.ELEVATOR.MODE = "elevator"
_C.PROFILE.ELEVATOR.CAST_POWER_LEVEL = 1.0
_C.PROFILE.ELEVATOR.CAST_DELAY = 4.0
_C.PROFILE.ELEVATOR.SINK_TIMEOUT = 60.0
_C.PROFILE.ELEVATOR.TIGHTEN_DURATION = 1.0
_C.PROFILE.ELEVATOR.ELEVATE_DURATION = 4.0
_C.PROFILE.ELEVATOR.ELEVATE_DELAY = 4.0
_C.PROFILE.ELEVATOR.ELEVEATE_TIMEOUT = 40.0
_C.PROFILE.ELEVATOR.ACCELERATION = "auto"
_C.PROFILE.ELEVATOR.HOOK_DELAY = 0.0
_C.PROFILE.ELEVATOR.TROLLING = "off"


# ---------------------------------------------------------------------------- #
#                             Float Fishing Profile                            #
# ---------------------------------------------------------------------------- #
_C.PROFILE.FLOAT = CN()
_C.PROFILE.FLOAT.MODE = "float"
_C.PROFILE.FLOAT.CAST_POWER_LEVEL = 5.0
_C.PROFILE.FLOAT.CAST_DELAY = 4.0
_C.PROFILE.FLOAT.FLOAT_SENSITIVITY = 0.65
_C.PROFILE.FLOAT.CHECK_DELAY = 1.0
_C.PROFILE.FLOAT.PULL_DELAY = 0.5
_C.PROFILE.FLOAT.DRIFTING_TIMEOUT = 16.0
_C.PROFILE.FLOAT.CAMERA_SHAPE = "square"



def get_cfg_defaults():
    """Get a yacs CfgNode object with default values for my_project."""
    # Return a clone so that the defaults will not be altered
    # This is for the "local variable" use pattern
    return _C.clone()
