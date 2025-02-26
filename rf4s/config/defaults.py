"""Default yacs config node."""

from yacs.config import CfgNode as CN

_C = CN()
_C.VERSION = "0.1.0"

_C.SCRIPT = CN()
_C.SCRIPT.LANGUAGE = "en"
_C.SCRIPT.LAUNCH_OPTIONS = ""
_C.SCRIPT.SMTP_VERIFICATION = True
_C.SCRIPT.IMAGE_VERIFICATION = True
_C.SCRIPT.SNAG_DETECTION = True
_C.SCRIPT.SPOOLING_DETECTION = True
_C.SCRIPT.RANDOM_ROD_SELECTION = True
_C.SCRIPT.SPOOL_CONFIDENCE = 0.985
_C.SCRIPT.SPOD_ROD_RECAST_DELAY = 1800 # 30 minutes
_C.SCRIPT.LURE_CHANGE_DELAY = 1800
_C.SCRIPT.ALARM_SOUND = "./static/sound/guitar.wav"


_C.KEY = CN()
_C.KEY.TEA = -1
_C.KEY.CARROT = -1
_C.KEY.BOTTOM_RODS = (1, 2, 3)
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
_C.STAT.TEA_DELAY = 300
_C.STAT.COFFEE_LIMIT = 10
_C.STAT.COFFEE_PER_DRINK = 1
_C.STAT.ALCOHOL_DELAY = 900 # 15 minutes
_C.STAT.ALCOHOL_PER_DRINK = 1


_C.FRICTION_BRAKE = CN()
_C.FRICTION_BRAKE.INITIAL = 29
_C.FRICTION_BRAKE.MAX = 30
_C.FRICTION_BRAKE.START_DELAY = 2.0
_C.FRICTION_BRAKE.INCREASE_DELAY = 1.0
_C.FRICTION_BRAKE.SENSITIVITY = "medium"


_C.KEEPNET = CN()
_C.KEEPNET.CAPACITY = 100
_C.KEEPNET.DELAY = 1.0
_C.KEEPNET.FULL_ACTION = "quit"
_C.KEEPNET.RELEASE_WHITELIST = (
    "mackerel", "saithe", "herring", "squid", "scallop", "mussel"
)


_C.NOTIFICATION = CN()
_C.NOTIFICATION.EMAIL = "email@example.com"
_C.NOTIFICATION.PASSWORD = "password"
_C.NOTIFICATION.SMTP_SERVER = "smtp.example.com"
_C.NOTIFICATION.MIAO_CODE = "example"


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
_C.PROFILE.SPIN.TIGHTEN_DURATION = 0.0
_C.PROFILE.SPIN.RETRIEVE_DURATION = 0.0
_C.PROFILE.SPIN.RETRIEVE_DELAY = 0.0
_C.PROFILE.SPIN.PRE_ACCELERATION = False
_C.PROFILE.SPIN.POST_ACCELERATION = "off"
_C.PROFILE.SPIN.TYPE = "normal"

_C.PROFILE.PAUSE_SPIN = CN()
_C.PROFILE.PAUSE_SPIN.MODE = "spin"
_C.PROFILE.PAUSE_SPIN.CAST_POWER_LEVEL = 5.0
_C.PROFILE.PAUSE_SPIN.CAST_DELAY = 6.0
_C.PROFILE.PAUSE_SPIN.TIGHTEN_DURATION = 1.0
_C.PROFILE.PAUSE_SPIN.RETRIEVE_DURATION = 1.0
_C.PROFILE.PAUSE_SPIN.RETRIEVE_DELAY = 3.0
_C.PROFILE.PAUSE_SPIN.PRE_ACCELERATION = False
_C.PROFILE.PAUSE_SPIN.POST_ACCELERATION = "off"
_C.PROFILE.PAUSE_SPIN.TYPE = "pause"


_C.PROFILE.LIFT_SPIN = CN()
_C.PROFILE.LIFT_SPIN.MODE = "spin"
_C.PROFILE.LIFT_SPIN.CAST_POWER_LEVEL = 5.0
_C.PROFILE.LIFT_SPIN.CAST_DELAY = 6.0
_C.PROFILE.LIFT_SPIN.TIGHTEN_DURATION = 0.0
_C.PROFILE.LIFT_SPIN.RETRIEVE_DURATION = 1.0
_C.PROFILE.LIFT_SPIN.RETRIEVE_DELAY = 1.0
_C.PROFILE.LIFT_SPIN.PRE_ACCELERATION = False
_C.PROFILE.LIFT_SPIN.POST_ACCELERATION = "off"
_C.PROFILE.LIFT_SPIN.TYPE = "lift"


# ---------------------------------------------------------------------------- #
#                            Bottom Fishing Profile                            #
# ---------------------------------------------------------------------------- #
_C.PROFILE.BOTTOM = CN()
_C.PROFILE.BOTTOM.MODE = "bottom"
_C.PROFILE.BOTTOM.CAST_POWER_LEVEL = 5.0
_C.PROFILE.BOTTOM.CAST_DELAY = 4.0
_C.PROFILE.BOTTOM.POST_ACCELERATION = "off"
_C.PROFILE.BOTTOM.CHECK_DELAY = 32.0
_C.PROFILE.BOTTOM.CHECK_MISS_LIMIT = 16


# ---------------------------------------------------------------------------- #
#                      Marine / Wakey Rig Pirking Profile                      #
# ---------------------------------------------------------------------------- #
_C.PROFILE.PIRK = CN()
_C.PROFILE.PIRK.MODE = "pirk"
_C.PROFILE.PIRK.CAST_POWER_LEVEL = 1.0
_C.PROFILE.PIRK.CAST_DELAY = 4.0
_C.PROFILE.PIRK.SINK_TIMEOUT = 60.0
_C.PROFILE.PIRK.TIGHTEN_DURATION = 1.0
_C.PROFILE.PIRK.CTRL = False
_C.PROFILE.PIRK.PIRK_DURATION = 0.5
_C.PROFILE.PIRK.PIRK_DELAY = 2.0
_C.PROFILE.PIRK.PIRK_TIMEOUT = 32.0
_C.PROFILE.PIRK.ADJUST = True
_C.PROFILE.PIRK.POST_ACCELERATION = "auto"
_C.PROFILE.PIRK.HOOK_DELAY = 0.0
_C.PROFILE.PIRK.DEPTH_ADJUST_DELAY = 4.0


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
_C.PROFILE.ELEVATOR.DROP = False
_C.PROFILE.ELEVATOR.POST_ACCELERATION = "auto"
_C.PROFILE.ELEVATOR.HOOK_DELAY = 0.0


# ---------------------------------------------------------------------------- #
#                             Float Fishing Profile                            #
# ---------------------------------------------------------------------------- #
_C.PROFILE.TELESCOPIC = CN()
_C.PROFILE.TELESCOPIC.MODE = "telescopic"
_C.PROFILE.TELESCOPIC.CAST_POWER_LEVEL = 5.0
_C.PROFILE.TELESCOPIC.CAST_DELAY = 4.0
_C.PROFILE.TELESCOPIC.FLOAT_SENSITIVITY = 0.68
_C.PROFILE.TELESCOPIC.CHECK_DELAY = 1.0
_C.PROFILE.TELESCOPIC.PULL_DELAY = 0.5
_C.PROFILE.TELESCOPIC.DRIFT_TIMEOUT = 16.0
_C.PROFILE.TELESCOPIC.CAMERA_SHAPE = "square"


# ---------------------------------------------------------------------------- #
#                           Bolognese Fishing Profile                          #
# ---------------------------------------------------------------------------- #
_C.PROFILE.BOLOGNESE = CN()
_C.PROFILE.BOLOGNESE.MODE = "bolognese"
_C.PROFILE.BOLOGNESE.CAST_POWER_LEVEL = 5.0
_C.PROFILE.BOLOGNESE.CAST_DELAY = 4.0
_C.PROFILE.BOLOGNESE.FLOAT_SENSITIVITY = 0.68
_C.PROFILE.BOLOGNESE.CHECK_DELAY = 1.0
_C.PROFILE.BOLOGNESE.PULL_DELAY = 0.5
_C.PROFILE.BOLOGNESE.DRIFT_TIMEOUT = 32.0
_C.PROFILE.BOLOGNESE.CAMERA_SHAPE = "square"



def get_cfg_defaults():
    """Get a yacs CfgNode object with default values for my_project."""
    # Return a clone so that the defaults will not be altered
    # This is for the "local variable" use pattern
    return _C.clone()
