import yaml
from yacs.config import CfgNode as CN
from config.defaults import get_cfg_defaults
from pathlib import Path
import sys
import argparse

import logging

logger = logging.getLogger(__name__)

def setup_cfg() -> CN:
    cfg = get_cfg_defaults()
    cfg.set_new_allowed(True)
    return cfg.clone()

def dict_to_cfg(args):
    cfg = CN()
    for k, v in args.items():
        k = k.upper()
        if isinstance(v, dict):
            cfg[k] = dict_to_cfg(v)
        else:
            cfg[k] = v
    return cfg

# def merge_from_file(cfg: CN, profile_name) -> CN:
#     with open(Path(__file__).resolve().parents[2] / "config.yaml") as f:
#         user_cfg = yaml.safe_load(f)

#     if not is_profile_name_valid(profile_name, user_cfg):
#         sys.exit(1)

#     user_profile = user_cfg[profile_name.upper()]
#     if not is_profile_valid(user_profile, cfg):
#         sys.exit(1)

#     cfg[user_profile["MODE"].upper()].merge_from_list(to_list(user_profile))
#     cfg["SCRIPT"]["MODE"] = user_profile["MODE"].upper()
#     return cfg

def is_profile_name_valid(profile_name, user_cfg):
    if profile_name.upper() not in user_cfg:
        logger.critical("Invalid profile name: '%s'", profile_name)
        return False
    return True

def is_profile_valid(user_profile, orig_cfg):
    mode = user_profile["MODE"].upper()
    if mode not in ("SPIN", "BOTTOM", "PIRK", "ELEVATOR", "FLOAT"):
        logger.critical("Invalid mode: '%s'", user_profile["MODE"])
        return False

    template = orig_cfg[mode]
    for key in user_profile:
        if key not in template:
            logger.critical("Invalid setting: '%s'", key)
            return False
    return True

def to_list(profile):
    pairs = []
    for k, v in profile.items():
        pairs.extend([k, v])
    return pairs