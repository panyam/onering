
import os
import shlex
import ipdb
import runner
from onering import utils as orutils
from utils import logerror

class OneringCommandRunner(runner.CommandRunner):
    """
    Commands to load onering schemas.
    """
    def do_load(self, console, cmd, rest, prev):
        """
        Loads one or more onering files.   A onering file could contain models, derivations, transformations, bindings etc.

        Usage:

            load  file      -   Load a single file
            load  folder    -   Load all files in a given folder.
        """
        import onering.dsl as dsl
        path = rest
        context = console.thering
        abspath = console.abspath(path)

        if console.isfile(path):
            dsl.parser.Parser(open(abspath), context).parse()
        elif console.isfile(path + ".onering"):
            dsl.parser.Parser(open(abspath + ".onering"), context).parse()
        elif console.isdir(path):
            for f in orutils.collect_files_by_extension(abspath, "onering"):
                dsl.parser.Parser(open(f), context).parse()
        else:
            logerror("Invalid path: %s" % abspath)
