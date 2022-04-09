"""Handle program wide resources (files, images, etc...)"""
import os

from appdirs import user_data_dir
from pkg_resources import ResourceManager

resource_manager = ResourceManager()

depot_path = user_data_dir('mlox', 'mlox')
if not os.path.isdir(depot_path):
    os.makedirs(depot_path)

# base_file = os.path.join(user_path, "mlox_base.txt")
# user_file = os.path.join(user_path, "mlox_user.txt")

# For the updater
UPDATE_BASE = "mlox-data.7z"
# update_file = os.path.join(user_path, UPDATE_BASE)
UPDATE_URL = 'https://svn.code.sf.net/p/mlox/code/trunk/downloads/' + UPDATE_BASE


def set_user_path(cwd):
    global depot_path

    depot_path = cwd
    if not os.path.isdir(depot_path):
        os.makedirs(depot_path)


def get_user_path() -> str:
    global depot_path
    return depot_path


def get_base_file() -> str:
    return os.path.join(depot_path, "mlox_base.txt")


def get_user_file() -> str:
    return os.path.join(depot_path, "mlox_user.txt")


def get_update_file() -> str:
    return os.path.join(depot_path, UPDATE_BASE)
