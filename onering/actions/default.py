
from __future__ import absolute_import
import os
import json
import shlex
import ipdb
from onering.console import runner, dirs, pegasus, courier, orc, platform
from onering.generator import utils as orgenutils
from onering.actions.base import ActionGroup

class DefaultActions(ActionGroup):
    def __init__(self, context):
        super(DefaultActions, self).__init__(context)

    def load(self, fqn_or_path):
        """
        Loads a script denoted by either its name (to be resolved by the schema resolver) or by an absolute path.
        If the parameter has SLASHES in it then the parameter is treated as a (absolute or relative) path, 
        otherwise it is treated as a fully qualified name(fqn).

        **Parameters:**
            fqn_or_path     FQN or path of the script to be loaded
        """
        fqn_or_path = fqn_or_path.strip()
        if not fqn_or_path:
            raise Exception("load command requires a script file to be loaded and executed")
        self._load_script(script)

    def _load_script(self, script_path):
        if not self.isfile(script_path):
            raise Exception("Invalid script file: %s, from path: %s" % (script_path, self.curdir))

        print "Loading script: ", script_path
        with self._read_file(script_path) as script_file_data:
            lines = [ l.strip() for l in script_file_data.split("\n") if l.strip() and not l.strip().startswith("#")]
            for line in lines:
                self.onecmd(line)

    def _read_file(self, file_path):
        class FileReadData(object):
            def __init__(self, context, file_path):
                self.context = context
                self.file_path = file_path

            def __enter__(self):
                # When a file is being read we want the file's parent folder to be 
                # the current folder
                import os
                dirname = os.path.dirname(file_path)
                abspath = self.context.abspath(self.file_path)
                file_obj = open(abspath)
                data = file_obj.read()
                file_obj.close()

                self.context.pushdir()
                self.context.curdir = dirname
                print "Entering Dir: ", self.context.curdir
                return data

            def __exit__(self, type, value, traceback):
                self.context.popdir()
                print "Entering Dir: ", self.context.curdir

        return FileReadData(self, file_path)

