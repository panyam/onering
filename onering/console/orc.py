
import os
import shlex
import ipdb
import runner
from onering.actions import loaders

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
        loaders.LoaderActions(context.thering).load_onering_path(rest)
