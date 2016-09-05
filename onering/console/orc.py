
import os
import shlex
import ipdb
import runner
from onering import utils as orutils
from utils import logerror

class OneringCommandRunner(runner.CommandRunner):
    def do_load(self, console, cmd, rest, prev):
        """
        Loads one or onering files.   A onering file could contain models, derivations, transformations, bindings etc.

        Usage:

            load  file      -   Load a single file
            load  folder    -   Load all files in a given folder.
        """
        import onering.dsl as dsl
        path = rest
        context = console.thering
        if os.path.isfile(path):
            dsl.parser.Parser(open(path), context).parse()
        elif os.path.isfile(path + ".onering"):
            dsl.parser.Parser(open(path + ".onering"), context).parse()
        else:
            for f in orutils.collect_files_by_extension(path, "onering"):
                dsl.parser.Parser(open(f), context).parse()
