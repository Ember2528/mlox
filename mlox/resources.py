"""Handle program wide resources (files, images, etc...)"""
import json
import logging
import os
from json import JSONDecodeError
from typing import Optional

from appdirs import user_data_dir
from pkg_resources import ResourceManager

res_logger = logging.getLogger('mlox.resources')


def get_settings_file() -> str:
    return os.path.join(depot_path, "mlox_settings.txt")


def settings_load():
    global settings

    if os.path.exists(get_settings_file()):
        try:
            with open(get_settings_file(), "r") as fs:
                settings = json.load(fs)
        except JSONDecodeError as e:
            res_logger.warning(f'Unable to deserialize graph from {get_graph_file()}.')
            res_logger.debug(f'Exception {str(e)}.')


resource_manager = ResourceManager()

depot_path = user_data_dir('mlox', 'mlox')
if not os.path.isdir(depot_path):
    os.makedirs(depot_path)

# For the updater
UPDATE_BASE = "mlox_base.txt"
UPDATE_USER = "mlox_user.txt"
UPDATE_MY_USER = "mlox_my_rules.txt"

UPDATE_URL = 'https://github.com/DanaePlays/mlox-rules/raw/main/'
UPDATE_URL_BASE = UPDATE_URL + UPDATE_BASE
UPDATE_URL_USER = UPDATE_URL + UPDATE_USER

# Settings
settings = {}
settings_load()


def set_user_path(path):
    global depot_path

    depot_path = path
    if not os.path.isdir(depot_path):
        os.makedirs(depot_path)

    settings_load()


def get_user_path() -> str:
    global depot_path
    return depot_path


def get_base_file() -> str:
    return os.path.join(depot_path, UPDATE_BASE)


def get_user_file() -> str:
    return os.path.join(depot_path, UPDATE_USER)


def get_my_user_file() -> str:
    return os.path.join(depot_path, UPDATE_MY_USER)


def get_graph_file() -> str:
    return os.path.join(depot_path, "mlox_graph.json")


def get_parser_msg_file() -> str:
    return os.path.join(depot_path, "mlox_parser_msg.txt")


def settings_save():
    with open(get_settings_file(), "w") as write:
        json.dump(settings, write, indent=4)


def settings_get_val(name: str) -> Optional[str]:
    return settings.get(name)


def settings_set_val(name: str, value, do_save=True):
    settings[name] = value
    if do_save:
        settings_save()

