import cmd
import code
import ipdb
import json
import sys
import shlex
import traceback
import default

from utils import logerror
from typelib import registry 
from typelib import core as tlcore
from typelib import errors as tlerrors

from onering import utils as orutils
from onering.utils import dirutils
from onering import resolver
from onering import context as orcontext
from onering import errors as orerrors

class OneringConsoleBase(dirutils.DirPointer):
    def __init__(self):
        super(OneringConsoleBase, self).__init__()
        self.thering = orcontext.OneringContext()
        self.currIndex = 1
        self.prompt = "OneRing :[%03d]> " % self.currIndex

    @property
    def type_registry(self):
        return self.thering.type_registry

    @property
    def entity_resolver(self):
        return self.thering.entity_resolver

    def parse_arguments_and_run(self):
        from optparse import OptionParser
        parser = OptionParser()
        parser.add_option("-s", "--script", dest = "script", help = "Run a particular onering script.")
        parser.add_option("-c", "--command", dest = "command", help = "Run the ';' seperated list of commands in the command line.")

        options,args = parser.parse_args()

        if options.script:
            self.onecmd("load %s" % options.script)
        elif options.command:
            commands = options.command.split(";")
            for command in commands:
                self.onecmd(command)
        else:
            self.cmdloop()

    def postcmd(self, stop, line):
        if line.strip():
            self.currIndex += 1
            self.prompt = "OneRing :[%03d]> " % self.currIndex

    def reset(self):
        self.thering.reset()

    def load_string(self, source_string):
        import onering.dsl as dsl
        context = self.thering
        dsl.parser.Parser(source_string, context).parse()


    def load_script(self, script_path):
        if not self.isfile(script_path):
            logerror("Invalid script file: %s, from path: %s" % (script_path, self.curdir))
            return

        print "Loading script: ", script_path
        with self.read_file(script_path) as script_file_data:
            lines = [ l.strip() for l in script_file_data.split("\n") if l.strip() and not l.strip().startswith("#")]
            for line in lines:
                self.onecmd(line)

    def read_file(self, file_path):
        class FileReadData(object):
            def __init__(self, console, file_path):
                self.console = console
                self.file_path = file_path

            def __enter__(self):
                # When a file is being read we want the file's parent folder to be 
                # the current folder
                import os
                dirname = os.path.dirname(file_path)
                abspath = self.console.abspath(self.file_path)
                file_obj = open(abspath)
                data = file_obj.read()
                file_obj.close()

                self.console.pushdir()
                self.console.curdir = dirname
                print "Entering Dir: ", self.console.curdir
                return data

            def __exit__(self, type, value, traceback):
                self.console.popdir()
                print "Entering Dir: ", self.console.curdir

        return FileReadData(self, file_path)

    def on_exit(self):
        """
        Called when the onering console quits.
        """
        print "Thou shall pass"

class OneringConsole(code.InteractiveConsole, OneringConsoleBase):
    def __init__(self):
        code.InteractiveConsole.__init__(self, locals = dict(globals(), **locals()))
        OneringConsoleBase.__init__(self)
        self.locals["thering"] = self.thering
        self.locals["entity_resolver"] = self.entity_resolver
        self.locals["type_registry"] = self.type_registry
        self.needs_more_input = False
        self.command_runner = default.DefaultCommandRunner()
        self.rawmode = False
        self.rawlines = []

    def enter_rawmode(self, endword):
        self.rawmode = True
        self.rawlines = []
        self.rawmode_end = endword

    def exit_rawmode(self):
        self.rawmode = False
        self.load_string("\n".join(self.rawlines))

    def push(self, line):
        if self.rawmode or self.needs_more_input:
            if line == self.rawmode_end:
                self.exit_rawmode()
                return False
            else:
                self.rawlines.append(line)
                return True

        line = line.strip()
        if line and not line.startswith("#"):
            lexer = shlex.shlex(line)
            cmd = lexer.next()
            rest = line[len(cmd):]

            self.needs_more_input = False
            
            if self.command_runner.can_run(cmd):
                try:
                    self.command_runner.run(self, cmd, rest)
                except tlerrors.TLException, exc:
                    logerror(exc.message)
                    traceback.print_exc()
                    raise
                except orerrors.OneringException, exc:
                    logerror(exc.message)
                    traceback.print_exc()
                    raise
                except:
                    traceback.print_exc()
                    raise
            else:
                self.needs_more_input = code.InteractiveConsole.push(self, line)
            if not self.needs_more_input:
                self.postcmd(False, line)
        else:
            self.needs_more_input = code.InteractiveConsole.push(self, line)
            return self.needs_more_input

    def raw_input(self, prompt):
        if self.rawmode:
            return code.InteractiveConsole.raw_input(self, " ... ")
        else:
            return code.InteractiveConsole.raw_input(self, self.prompt)

    def onecmd(self, line):
        self.push(line)

    def cmdloop(self):
        self.interact()
        self.on_exit()
