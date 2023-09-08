import logging
import os
import re
from functools import reduce

config_logger = logging.getLogger('mlox.configHandler')

MIN_SAFE_TIMESTAMP = 315529200  # safe file timestamp for both NTFS and FAT32 fs


def caseless_uniq(un_uniqed_files):
    """
    Given a list, return a list of unique strings, and a list of duplicates.
    This is a caseless comparison, so 'Test' and 'test' are considered duplicates.
    """
    lower_files = []  # Use this to allow for easy use of the 'in' keyword
    unique_files = []  # Guaranteed case insensitive unique
    filtered = []  # any duplicates from the input

    for aFile in un_uniqed_files:
        if aFile.lower() in lower_files:
            filtered.append(aFile)
        else:
            unique_files.append(aFile)
            lower_files.append(aFile.lower())
    return unique_files, filtered

def partition_masters(file_list):
    masters = []
    non_masters = []
    master_extensions = [".esm", ".omwgame"]

    for filename in file_list:
        _, ext = os.path.splitext(filename)
        if ext.lower() in master_extensions:
            masters.append(filename)
        else:
            non_masters.append(filename)

    return masters, non_masters

class configHandler():
    """
    A class for handling plugin configuration files.

    A configuration file is a text file containing an ordered list of plugins.
    For example 'Morrowind.ini' is a configuration File.
    This allows for reading and writing to those files.
    """

    # A section of a configuration file
    section_re = re.compile("^(\[.*\])\s*$", re.MULTILINE)
    # pattern matching a plugin in Morrowind.ini
    re_gamefile = re.compile(r'(?:GameFile\d+=)(.*)', re.IGNORECASE)
    # pattern to match plugins in FromFile (somewhat looser than re_gamefile)
    # this may be too sloppy, we could also look for the same prefix pattern,
    # and remove that if present on all lines.
    re_sloppy_plugin = re.compile(
        r'^(?:(?:DBG:\s+)?[_\*]\d\d\d[_\*]\s+|GameFile\d+=|content=|\d{1,3} {1,2}|Plugin\d+\s*=\s*)?(.+\.(?:es[mp]|omwaddon|omwscripts)\b)',
        re.IGNORECASE)
    # pattern to match plugins in openmw.cfg
    re_openmw_plugin = re.compile(r'(?:content=)(.*)', re.IGNORECASE)
    # pattern used to match a string that should only contain a plugin name, no slop
    re_plugin = re.compile(r'^(\S.*?\.(?:es[mp]|omwaddon|omwscripts)\b)([\s]*)', re.IGNORECASE)

    # pattern to match data lines in openmw.cfg
    re_openmw_data = re.compile(r'(?:data=")(.*)"', re.IGNORECASE)
    re_openmw_groundcover = re.compile(r'(?:groundcover=)(.*)', re.IGNORECASE)

    # The regular expressions used to parse the file
    read_regexes = {
        "Morrowind": re_gamefile,
        "OpenMw": re_openmw_plugin,
        "Oblivion": re_plugin,
        "raw": re_plugin,
        None: re_sloppy_plugin
    }
    # The regular expressions used to parse the file for content lines
    read_regexes_data = {
        "Morrowind": re_openmw_data,
        "OpenMw": re_openmw_data,
        "Oblivion": re_openmw_data,
        "raw": re_openmw_data,
        None: re_openmw_data
    }
    # The path to the configuration file
    configFile = None
    # The type of config file (Is it a 'Morrowind.ini', raw, or something else?)
    fileType = None

    def __init__(self, configFile, fileType=None):
        self.configFile = configFile
        try:
            self.read_regexes[
                fileType]  # Note:  This might not seem to do anything, but it serves as a runtime check that fileType is an accepted value.
            self.fileType = fileType
        except:
            config_logger.warning("\"{0}\" is not a recognized file type!".format(fileType))

    @staticmethod
    def _sort_by_date(dir_path, list_of_plugins):
        """Sort a list of plugin files by modification date"""
        dated_plugins = [(os.path.getmtime(os.path.join(dir_path, a_plugin)), a_plugin) for a_plugin in list_of_plugins]
        dated_plugins.sort()
        return [x[1] for x in dated_plugins]

    @staticmethod
    def _sort_by_date_fullpath(list_of_plugins):
        """Sort a list of plugin files by modification date"""
        dated_plugins = [(os.path.getmtime(a_plugin), a_plugin) for a_plugin in list_of_plugins]
        dated_plugins.sort()
        return [x[1] for x in dated_plugins]

    def read(self):
        """
        Read a configuration file

        :return: An ordered list of plugins
        """
        files = []
        regex = self.read_regexes[self.fileType]
        try:
            file_handle = open(self.configFile, 'r')
            for line in file_handle:
                gamefile = regex.match(line.strip())
                if gamefile:
                    f = gamefile.group(1).strip()
                    files.append(f)
            file_handle.close()
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return []
        except UnicodeDecodeError:
            config_logger.error("Bad Characters in configuration file: {0}".format(self.configFile))
            return []
        # Deal with duplicates
        (files, dups) = caseless_uniq(files)
        for f in dups:
            config_logger.debug("Duplicate plugin found in config file: {0}".format(f))
        return files

    def read_data(self):
        """
        Read a configuration file

        :return: An ordered list of content paths from the openmw.cfg
        """
        paths = []
        groundcovers = []

        regex = self.read_regexes_data[self.fileType]
        groundcover_regex = self.re_openmw_groundcover
        try:
            file_handle = open(self.configFile, 'r')
            for line in file_handle:
                datapath = regex.match(line.strip())
                if datapath:
                    f = datapath.group(1).strip()
                    paths.append(f)

                groundcover = groundcover_regex.match(line.strip())
                if groundcover:
                    f = groundcover.group(1).strip()
                    groundcovers.append(f.lower())

            file_handle.close()
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return []
        except UnicodeDecodeError:
            config_logger.error("Bad Characters in configuration file: {0}".format(self.configFile))
            return []
        # Deal with duplicates
        (paths, dups) = caseless_uniq(paths)
        for f in dups:
            config_logger.debug("Duplicate plugin found in config file: {0}".format(f))

        # actually get the files
        data_files_temp = []
        # loop through all data paths and get the plugins
        for datapath in paths:
            # check if directory still exists
            if not os.path.isdir(datapath):
                logging.warning("Data folder in cnfig does not exist anymore: {0}".format(datapath))
                continue

            # get plugins in directory
            files = [f for f in os.listdir(datapath) if os.path.isfile(os.path.join(datapath, f)) and f.lower() not in groundcovers ]
            (files, dups) = caseless_uniq(files)
            # Deal with duplicates
            for f in dups:
                logging.warning("Duplicate plugin found in data directory: {0}".format(f))

            (masters, non_masters) = partition_masters(files)

            files = []
            files.extend(masters)
            files.extend(non_masters)

            # add full paths
            for f in files:
                data_files_temp.append(os.path.join(datapath, f))

        # todo sort esms first
        files = []
        for f in self._sort_by_date_fullpath(data_files_temp):
            files.append(os.path.basename(f))

        (files, dups) = caseless_uniq(files)
        # Deal with duplicates
        for f in dups:
            logging.warning("Duplicate plugin found in data directory: {0}".format(f))

        return files

    def clear(self):
        """
        Remove all the plugin lines from a configuration file.

        :return: True on success, or False on failure
        """
        config_logger.debug("Clearing configuration file: {0}".format(self.configFile))
        return self.write([])

    def write(self, list_of_plugins):
        """
        Write a list of plugins to a configuration file

        :return: True on success, or False on failure
        """
        config_logger.debug("Writing configuration file: {0}".format(self.configFile))

        if self.fileType == "Morrowind":
            return self._write_morrowind(list_of_plugins)

        if self.fileType == "OpenMw":
            return self._write_openmw(list_of_plugins)

        if self.fileType == "raw":
            return self._write_raw(list_of_plugins)

        config_logger.error("Can not write to %s configuration files.", self.fileType)
        return False

    def _write_morrowind(self, list_of_plugins):
        """
        Write a list of plugins to a Morrowind.ini file

        We don't just use `configparser` because it breaks on reading Morrowind.ini files :/

        :return: True on success, or False on failure
        """
        # Generate the plugins string
        out_str = "\n"
        for i in range(0, len(list_of_plugins)):
            out_str += "GameFile{index}={plugin}\n".format(index=i, plugin=list_of_plugins[i])

        # Open and read a configuration file, splitting the result into multiple sections.
        try:
            file_handle = open(self.configFile, 'r')
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return False
        file_buffer = file_handle.read()
        file_handle.close()
        sections = self.section_re.split(file_buffer)

        # Replace the data in the '[Game Files]' section with the generated plugins string
        try:
            config_index = sections.index('[Game Files]')
        except IndexError:
            config_logger.error("Configuration file does not have a '[Game Files]' section!")
            return False
        sections[config_index + 1] = out_str
        file_buffer = reduce(lambda x, y: x + y, sections)

        # Write the modified buffer to the configuration file
        try:
            file_handle = open(self.configFile, 'w')
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return False
        file_handle.write(file_buffer)
        file_handle.close()

        return True

    def _write_raw(self, list_of_plugins):
        """
        Write a list of plugins to a raw file

        That is a file containing nothing but plugins.  One per line

        :return: True on success, or False on failure
        """
        try:
            file_handle = open(self.configFile, 'w')
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return False

        for a_plugin in list_of_plugins:
            print(a_plugin, file=file_handle)
        file_handle.close()

        return True

    def _write_openmw(self, list_of_plugins):
        """
        Write a list of plugins to an openMW cfg file

        :return: True on success, or False on failure
        """

        # Generate the plugins string
        out_str = ""
        for i in range(0, len(list_of_plugins)):
            out_str += "content={plugin}\n".format(plugin=list_of_plugins[i])

        # Open and read a configuration file, splitting the result into multiple sections.
        try:
            file_handle = open(self.configFile, 'r')
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return False
        file_buffer = file_handle.readlines()
        file_handle.close()

        # Replace all lines starting with "content=" with the generated plugins string
        old_list = [item for item in file_buffer if not item.startswith("content=") ]
        old_str = ""
        for i in range(0, len(old_list)):
            old_str += "{line}".format(line=old_list[i])

        # Write the modified buffer to the configuration file
        try:
            file_handle = open(self.configFile, 'w')
        except IOError:
            config_logger.error("Unable to open configuration file: {0}".format(self.configFile))
            return False
        file_handle.write(old_str)
        file_handle.write(out_str)
        file_handle.close()

        return True


class dataDirHandler:
    """
    A class for handling a directory containing plugin files.

    Plugin files are loaded by Morrowind.exe in the order of their modification timestamp.
    With the oldest being loaded first.
    This allows for reading and setting the plugin order using the same interface as configHandler.
    """
    path = None

    def __init__(self, data_files_path, game_type=None):
        self.path = data_files_path
        self.game_type = game_type

    # Get the directory name in a printable form
    def getDir(self):
        return self.path

    def _full_path(self, a_file):
        """Convenience function to return the full path to a file."""
        return os.path.join(self.path, a_file)

    def _sort_by_date(self, list_of_plugins):
        """Sort a list of plugin files by modification date"""
        dated_plugins = [(os.path.getmtime(self._full_path(a_plugin)), a_plugin) for a_plugin in list_of_plugins]
        dated_plugins.sort()
        return ([x[1] for x in dated_plugins])

    def read(self):
        """
        Obtain an ordered list of plugins from a directory.

        Note:  Unlike configHandler.read(), ESM files will always be at the front of the returned list.
        :return: An ordered list of plugins
        """
        files = [f for f in os.listdir(self.path) if os.path.isfile(self._full_path(f))]
        (files, dups) = caseless_uniq(files)
        # Deal with duplicates
        for f in dups:
            logging.warning("Duplicate plugin found in data directory: {0}".format(f))

        # TODO: Sort by date first then change partition func to return one list avoid all this concatenation
        # sort the plugins into load order by modification date (esm's first)
        (masters, non_masters) = partition_masters(files)

        # OpenMW uses only cfg order
        if self.game_type == "OpenMw":
            files = masters + non_masters
        else:
            files = self._sort_by_date(masters)
            files += self._sort_by_date(non_masters)

        return files

    def write(self, list_of_plugins):
        """
        Change the modification times of plugin files to be in order of file list, oldest to newest

        There are six files with fixed times, the bsa files depend on the esm files being present.
        These files are fixed to be compatible with `tes3cmd resetdates`.
        :return: True on success, or False on failure
        """
        tes3cmd_resetdates_morrowind_mtime = 1024695106  # Fri Jun 21 17:31:46 2002
        tes3cmd_resetdates_tribunal_mtime = 1035940926  # Tue Oct 29 20:22:06 2002
        tes3cmd_resetdates_bloodmoon_mtime = 1051807050  # Thu May  1 12:37:30 2003

        mtime = tes3cmd_resetdates_morrowind_mtime
        try:
            for a_plugin in list_of_plugins:
                if a_plugin.lower() == "morrowind.esm":
                    mtime = tes3cmd_resetdates_morrowind_mtime
                    os.utime(self._full_path("Morrowind.bsa"), (MIN_SAFE_TIMESTAMP, mtime))
                elif a_plugin.lower() == "tribunal.esm":
                    mtime = tes3cmd_resetdates_tribunal_mtime
                    os.utime(self._full_path("Tribunal.bsa"), (MIN_SAFE_TIMESTAMP, mtime))
                elif a_plugin.lower() == "bloodmoon.esm":
                    mtime = tes3cmd_resetdates_bloodmoon_mtime
                    os.utime(self._full_path("Bloodmoon.bsa"), (MIN_SAFE_TIMESTAMP, mtime))
                else:
                    mtime += 60  # standard 1 minute Mash step
                os.utime(self._full_path(a_plugin), (MIN_SAFE_TIMESTAMP, mtime))
        except TypeError:
            config_logger.error(
                """
                Could not update load order!
                Are you sure you have \"Morrowind.bsa\", \"Tribunal.bsa\", and/or \"Bloodmoon.bsa\" in your data file directory?
                """)
            return False
        return True
