#!/usr/bin/python3
import logging
import os
import sys

from mlox import version
from mlox.loadOrder import Loadorder
from mlox.resources import set_user_path, get_user_path, get_update_file
from mlox.translations import _


def lint():
    """
    Process a load order.
    and returns an error code dependent on warnings or errors obtained.
    """

    # Configure logging from python module
    logging.getLogger('').setLevel(logging.DEBUG)
    console_log_stream = logging.StreamHandler()
    console_log_stream.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console_log_stream)
    # Disable parse debug logging unless the user asks for it (It's so much it actually slows the program down)
    logging.getLogger('mlox.parser').setLevel(logging.INFO)

    # override user_path dir
    set_user_path(os.getcwd())

    # Check Python version
    logging.debug(version.version_info())
    logging.info("Database Directory: %s", get_user_path())
    python_version = sys.version[:3]
    if float(python_version) < 3:
        logging.error("This program requires at least Python version 3.")
        sys.exit(1)

    logging.info("%s %s", version.full_version(), _["Hello!"])

    my_loadorder = Loadorder()
    log = my_loadorder.update(None, True, True, False)

    print(log)

    error_code = 0
    # check warnings and errors
    has_warnings = False
    has_errors = False
    for line in log.split('\n'):
        if "WARNING" in line:
            has_warnings = True
        if "ERROR" in line:
            has_errors = True

    if has_errors:
        error_code = 1
    elif has_warnings:
        error_code = 2

    sys.exit(error_code)


if __name__ == "__main__":
    lint()
