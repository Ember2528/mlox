# Utility classes For doing caseless filename processing:
# caseless_filename uses a dictionary that stores the truename of a
# plugin by its canonical lowercased form (cname). We only use the
# truename for output, in all other processing, we use the cname so
# that all processing of filenames is caseless.

# Note that the first function to call cname() is get_data_files()
# this ensures that the proper truename of the actual file in the
# filesystem is stored in our dictionary. cname() is subsequently
# called for all filenames mentioned in rules, which may differ by
# case, since human input is inherently sloppy.

import logging
import os
import re
from typing import Optional

import userpaths

file_logger = logging.getLogger('mlox.fileFinder')


class caseless_filenames:

    def __init__(self):
        self.truenames = {}

    def cname(self, truename):
        the_cname = truename.lower()
        if not the_cname in self.truenames:
            self.truenames[the_cname] = truename
        return (the_cname)

    def truename(self, cname):
        return (self.truenames[cname])


class caseless_dirlist:

    def __init__(self, dir=os.getcwd()):
        self.files = {}
        if dir is None:
            return
        if isinstance(dir, list):
            for directory in dir:
                self.append_files_from_directory(directory)
        if isinstance(dir, caseless_dirlist):
            self.dir = dir.dirpath()
        else:
            self.dir = os.path.normpath(os.path.abspath(dir))
        self.append_files_from_directory(dir)

    def append_files_from_directory(self, directory):
        for f in [p for p in os.listdir(directory)]:
            self.files[f.lower()] = f

    def find_file(self, file_name) -> Optional[str]:
        """
        Get a case sensitive file name
        :param file_name: A case insensitive file name
        :returns: A case sensitive file name, or None
        """
        return self.files.get(file_name.lower(), None)

    def find_path(self, file_name) -> Optional[str]:
        """
        Get the path to a file
        :param file_name: A case insensitive file name
        :returns: A case sensitive path, or None
        """
        f = file_name.lower()
        if f in self.files:
            return os.path.join(self.dir, self.files[f])
        return None

    def find_parent_dir(self, file_name):
        """
        :returns: The caseless_dirlist of the directory that contains file, starting from self.dir and working back
        towards root.
        """
        path = self.dir
        prev = None
        while path != prev:
            dl = caseless_dirlist(path)
            if dl.find_file(file_name):
                return (dl)
            prev = path
            path = os.path.split(path)[0]
        return None

    def dirpath(self):
        return self.dir

    def filelist(self):
        return self.files.values()


def _find_appdata():
    """a somewhat hacky function for finding where Oblivion's Application Data lives.
    Hopefully works under Windows, Wine, and native Linux."""
    if os.name == "posix":
        # Linux - total hack for finding plugins.txt
        # we assume we're running under a wine tree somewhere. so we
        # find where we are now, then walk the tree upwards to find system.reg
        # then grovel around in system.reg until we find the localappdata path
        # and then fake it like a Republican
        re_appdata = re.compile(r'"LOCALAPPDATA"="([^"]+)"', re.IGNORECASE)
        regdir = caseless_dirlist().find_parent_dir("system.reg")
        if regdir == None:
            return (None)
        regpath = regdir.find_path("system.reg")
        if regpath == None:
            return (None)
        try:
            inp = open(regpath, 'r')
            for line in inp:
                match = re_appdata.match(line)
                if match:
                    path = match.group(1)
                    path = path.split(r'\\')
                    drive = "drive_" + path.pop(0).lower()[0]
                    appdata = "/".join([regdir.dirpath(), drive, "/".join(path)])
                    inp.close()
                    return (appdata)
            inp.close()
        except IOError:
            pass
        return (None)
    # Windows
    try:
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
            vals = winreg.QueryValueEx(key, 'Local AppData')
        except WindowsError:
            return None
        else:
            key.Close()
        re_env = re.compile(r'%([^|<>=^%]+)%')
        appdata = re_env.sub(lambda m: os.environ.get(m.group(1), m.group(0)), vals[0])
        return (os.path.expandvars(appdata))
    except ImportError:
        return None


def _get_Oblivion_plugins_file():
    appdata = _find_appdata()
    if appdata is None:
        file_logger.warning("Application data directory not found")
        return None
    return os.path.join(appdata, "Oblivion", "Plugins.txt")


def _find_openmw_dir():
    return caseless_dirlist( os.path.join(userpaths.get_my_documents(), "my games", "OpenMW" ))

def find_game_dirs(openmw = False, vfs = False):
    """
    Attempt to find the plugin file and directory for Morrowind and Oblivion
    This will attempt to find Morrowind's files first
    """
    game = None
    gamedir = None
    datadir = None
    list_file = None

    cwd = caseless_dirlist()  # start our search in our current directory
    if openmw:
        game = "OpenMw"
        gamedir = cwd.find_parent_dir("openmw.cfg")
        if gamedir:
            list_file = gamedir.find_path("openmw.cfg")
            import configHandler
            datadir = configHandler.get_data_entries_from_config(list_file)
    else:
        game = "Morrowind"
        gamedir = cwd.find_parent_dir("Morrowind.ini")
        if gamedir:
            datadir = gamedir.find_path("Data Files")
            list_file = gamedir.find_path("Morrowind.ini")

    file_logger.debug("Found Game:  {0}".format(game))
    file_logger.debug("Plugins file at:  {0}".format(list_file))
    # file_logger.debug("Data Files at: {0}".format(datadir))

    return game, list_file, datadir
