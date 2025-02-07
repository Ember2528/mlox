import logging
import os
import io

from mlox import configHandler, ruleParser, fileFinder
from mlox.resources import get_base_file, get_user_file, get_my_user_file

old_loadorder_output = "current_loadorder.out"
new_loadorder_output = "mlox_new_loadorder.out"

order_logger = logging.getLogger('mlox.loadOrder')


class Loadorder:
    """Class for reading plugin mod times (load order), and updating them based on rules"""

    def __init__(self):
        # order is the list of plugins in Data Files, ordered by mtime
        self.order = []  # the load order
        self.new_order = []  # the new load order
        self.is_sorted = False
        self.caseless = fileFinder.caseless_filenames()
        self.hints = {}  # hints in the load order for highlighting

        # self.datadir = None                # where plugins live
        # self.plugin_file = None            # Path to the file containing the plugin list
        # self.game_type = None              # 'Morrowind', 'Oblivion', or None for unknown
        self.game_type, self.plugin_file, self.datadir = fileFinder.find_game_dirs()

    def get_active_plugins(self):
        """
        Get the active list of plugins from the game configuration.

        "Active Plugins" are plugins that are both in the Data Files directory and in Morrowind.ini
        Updates self.order
        """
        self.is_sorted = False
        if self.plugin_file is None:
            order_logger.warning(
                "No game configuration file was found!\nAre you sure you're running mlox in or under your game directory?")
            return

        # Get all the plugins
        config_files = configHandler.configHandler(self.plugin_file, self.game_type).read()
        dir_files = configHandler.dataDirHandler(self.datadir).read()

        # Remove plugins not in the data directory (and correct capitalization)
        config_files = list(map(str.lower, config_files))
        self.order = filter(lambda x: x.lower() in config_files, dir_files)

        # Convert the files to lowercase, while storing them in a dict
        self.order = list(map(self.caseless.cname, self.order))

        order_logger.info("Found {0} plugins in: \"{1}\"".format(len(self.order), self.plugin_file))
        if not self.order:
            order_logger.warning("No active plugins, defaulting to all plugins in Data Files directory.")
            self.get_data_files()

    def get_data_files(self):
        """
        Get the load order from the data files directory.

        Updates self.order
        """
        self.is_sorted = False
        self.order = configHandler.dataDirHandler(self.datadir).read()

        # Convert the files to lowercase, while storing them in a dict
        self.order = list(map(self.caseless.cname, self.order))

        order_logger.info("Found {0} plugins in: \"{1}\"".format(len(self.order), self.datadir))

    def read_from_file(self, fromfile):
        """
        Get the load order by reading an input file.

        Clears self.game_type and self.datadir.
        Updates self.plugin_file and self.order
        """
        self.is_sorted = False
        self.game_type = None
        self.datadir = None  # This tells the parser to not worry about things like [SIZE] checks, or trying to read the plugin descriptions
        self.plugin_file = fromfile

        self.order = configHandler.configHandler(fromfile).read()
        if not self.order:
            order_logger.warning(
                "No plugins detected.\nmlox understands lists of plugins in the format used by Morrowind.ini or Wrye Mash.\nIs that what you used for input?")

        # Convert the files to lowercase, while storing them in a dict
        self.order = list(map(self.caseless.cname, self.order))

        order_logger.info("Found {0} plugins in: \"{1}\"".format(len(self.order), self.plugin_file))
        order_logger.info(
            "(Note: When the load order input is from an external source, the [SIZE] predicate cannot check the plugin filesizes, so it defaults to True).")

    def listversions(self):
        """List the versions of all plugins in the current load order"""
        out = "{0:20} {1:20} {2}\n".format("Name", "Description", "Plugin Name")
        for p in self.order:
            (file_ver, desc_ver) = ruleParser.get_version(p, self.datadir)
            out += "{0:20} {1:20} {2}\n".format(str(file_ver), str(desc_ver), self.caseless.truename(p))
        return out

    def add_current_order(self, graph, out_stream=None):
        """
        Add the current load order as a pseudo rule set.

        This lets us maintain the original ordering in the case where the rules say it doesn't matter.
        It also means we don't exclude any plugins that aren't in the rules.

        We treat the current load order as a sort of preferred order in
        the case where there are no rules. However, we have to be careful
        when there exists a [NEARSTART] or [NEAREND] rule for a plugin,
        that we do not introduce a new edge, we only add the node itself.
        This allows us to move unconnected nodes to the top or bottom of
        the roots calculated in the topo_sort routine, depending on
        whether they show up in [NEARSTART] or [NEAREND] rules,
        respectively"""
        if len(self.order) < 2:
            return
        order_logger.debug("adding edges from CURRENT ORDER")

        # make ordering pseudo-rules for esms to follow official .esms
        if self.game_type == "Morrowind":
            graph.add_edge("", "morrowind.esm", "tribunal.esm", out_stream)
            graph.add_edge("", "tribunal.esm", "bloodmoon.esm", out_stream)
            # Make all user's .esm files depend on bloodmoon.esm
            for p in self.order:
                if p[-4:] == ".esm":
                    if p not in ("morrowind.esm", "tribunal.esm", "bloodmoon.esm"):
                        graph.add_edge("", "bloodmoon.esm", p, out_stream)

        # make ordering pseudo-rules from nearend info
        kingyo_fun = [x for x in graph.nearend if x in self.order]
        for p_end in kingyo_fun:
            for p in [x for x in self.order if x != p_end]:
                graph.add_edge("", p, p_end, out_stream)
        # make ordering pseudo-rules from current load order.
        prev_i = 0
        graph.nodes.setdefault(self.order[prev_i], [])
        for curr_i in range(1, len(self.order)):
            graph.nodes.setdefault(self.order[curr_i], [])
            if self.order[curr_i] not in graph.nearstart and self.order[curr_i] not in graph.nearend:
                # add an edge, on any failure due to cycle detection, we try
                # to make an edge between the current plugin and the first
                # previous ancestor we can successfully link and edge from.
                for i in range(prev_i, 0, -1):
                    if self.order[i] not in graph.nearstart and self.order[i] not in graph.nearend:
                        if graph.add_edge("", self.order[i], self.order[curr_i], out_stream):
                            break
            prev_i = curr_i

    def get_original_order(self):
        """Get the original plugin order in a nice printable format"""
        formatted = []
        for n in range(1, len(self.order) + 1):
            formatted.append("{0:0>3} {1}".format(n, self.caseless.truename(self.order[n - 1])))
        return formatted

    def get_new_order(self):
        """Get the new plugin order in a nice printable format.
        Also, highlight mods that have moved up in the load order."""
        formatted = []
        orig_index = {}
        for n in range(1, len(self.order) + 1):
            orig_index[self.order[n - 1]] = n

        highlight = "_"
        for i in range(0, len(self.new_order)):

            p = self.new_order[i]
            curr = p.lower()
            if (orig_index[curr] - 1) > i:
                highlight = "*"

            if p in self.hints["conflicts"]:
                formatted.append("%s%03d%s %s" % ("*!", orig_index[curr], "*!", p))
            elif p in self.hints["patch"]:
                formatted.append("%s%03d%s %s" % ("!!", orig_index[curr], "!!", p))
            elif p in self.hints["requires"]:
                formatted.append("%s%03d%s %s" % ("!!!", orig_index[curr], "!!!", p))
            else:
                formatted.append("%s%03d%s %s" % (highlight, orig_index[curr], highlight, p))

            if highlight == "*":
                if i < len(self.new_order) - 1:
                    next_idx = self.new_order[i + 1].lower()
                if orig_index[curr] > orig_index[next_idx]:
                    highlight = "_"
        return formatted

    def explain(self, plugin_name, base_only=False):
        """Explain why a mod is in its current position"""
        parser = ruleParser.RuleParser(self.order, self.datadir, self.caseless)
        if os.path.exists(get_user_file()):
            parser.read_rules(get_user_file())
        parser.read_rules(get_base_file())
        plugin_graph = parser.get_graph()

        if not base_only:
            self.add_current_order(plugin_graph)  # tertiary order "pseudo-rules" from current load order

        output = plugin_graph.explain(plugin_name, self.order)
        return output

    def update(self, progress=None, warningsonly=False):
        """
        Update the load order based on input rules.
        """
        self.is_sorted = False
        if not warningsonly:
            if not self.order:
                err = "No plugins detected!\nmlox needs to run somewhere under where the game is installed."
                order_logger.error(err)
                return f"ERROR {err}"
            order_logger.debug("Initial load order:")
            for p in self.get_original_order():
                order_logger.debug("  " + p)

        out_stream = io.StringIO()

        # read rules from various sources, and add orderings to graph
        # if any subsequent rule causes a cycle in the current graph, it is discarded
        parser = ruleParser.RuleParser(self.order, self.datadir, self.caseless)

        # read my user file
        if progress is not None:
            progress.update_value_and_label(1, "Loading my rules file ...")
        if os.path.exists(get_my_user_file()):
            parser.read_rules(get_my_user_file(), None)

        # read user file
        if progress is not None:
            progress.update_value_and_label(25, "Loading user file ...")
        if os.path.exists(get_user_file()):
            parser.read_rules(get_user_file(), None)

        # read base file
        if progress is not None:
            progress.update_value_and_label(50, "Loading base file ...")
        if not parser.read_rules(get_base_file(), None):
            err = "Unable to parse 'mlox_base.txt', load order NOT sorted!"
            order_logger.error(err)
            self.new_order = []
            return f"ERROR {err}"
        if progress is not None:
            progress.update_value_and_label(90, "Parsing rules ...")

        # Convert the graph into a sorted list of all plugins (rules + load order)
        self.hints = parser.hints
        plugin_graph = parser.get_graph()
        print(parser.get_messages(), file=out_stream)

        self.add_current_order(plugin_graph, out_stream)  # tertiary order "pseudo-rules" from current load order
        sorted_plugins = plugin_graph.topo_sort()

        if warningsonly:
            return out_stream.getvalue()

        # The "sorted" list will be a superset of all known plugin files,
        # but we only care about active plugins.
        sorted_datafiles = [f for f in sorted_plugins if f in self.order]
        (esm_files, esp_files) = configHandler.partition_esps_and_esms(sorted_datafiles)
        new_order_cname = esm_files + esp_files
        self.new_order = list(map(self.caseless.truename, new_order_cname))

        order_logger.debug("New load order:")
        for p in self.get_new_order():
            order_logger.debug("  " + p)

        if len(self.new_order) != len(self.order):
            err = f"sanity check: len(self.new_order {len(self.new_order)}) != len(self.order {len(self.order)})"
            order_logger.error("sanity check: len(self.new_order %d) != len(self.order %d)", len(self.new_order),
                               len(self.order))
            self.new_order = []
            return f"ERROR {err}"

        if self.order == new_order_cname:
            order_logger.info("[Plugins already in sorted order. No sorting needed!]")
            self.is_sorted = True

        if self.datadir:
            # these are things we do not want to do if just testing a load order from a file
            # save the load orders to file for future reference
            configHandler.configHandler(old_loadorder_output, "raw").write(self.order)
            configHandler.configHandler(new_loadorder_output, "raw").write(self.new_order)

        return out_stream.getvalue()

    def write_new_order(self):
        """Write/save the new order to the directory and config file."""
        if not isinstance(self.new_order, list) or self.new_order == []:
            order_logger.error("Not saving blank load order.")
            return False
        if self.datadir:
            if configHandler.dataDirHandler(self.datadir).write(self.new_order):
                self.is_sorted = True
        if isinstance(self.plugin_file, str):
            if configHandler.configHandler(self.plugin_file, self.game_type).write(self.new_order):
                self.is_sorted = True

        if not self.is_sorted:
            order_logger.error("Unable to save new load order.")
            return False
        return True
