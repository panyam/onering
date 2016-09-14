import cmd
import code
import ipdb
import json
import os, sys
import shlex
import traceback
import default

from utils import logerror
from typelib import registry 
from typelib import core as tlcore
from typelib import errors as tlerrors

from onering import utils as orutils
from onering import resolver
from onering import core as orcore
from onering import errors as orerrors

# Create the all important type registry and entity resolver (for loading pegasus models)

class OneringContext(orcore.Onering):
    def __init__(self):
        super(OneringContext, self).__init__()
        self.output_dir = "./gen"
        self.platform_aliases = {
            "java": "onering.backends.java.JavaTargetBackend"
        }
        self.template_dirs = []
        from onering.templates import loader as tplloader
        self.template_loader = tplloader.TemplateLoader(self.template_dirs)

class OneringConsoleBase(object):
    def __init__(self):
        self.thering = OneringContext()
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

    def curdir(self):
        return os.path.abspath(os.curdir)

    def load_script(self, script_path):
        if not os.path.isfile(script_path):
            logerror("Invalid script file: %s, from path: %s" % (script_path, self.curdir()))
            return
        else:
            print "Loading script: ", script_path
            with open(script_path) as script_file:
                prevdir = self.curdir()
                os.chdir(os.path.abspath(os.path.dirname(script_path)))
                lines = [ l.strip() for l in script_file.read().split("\n") if l.strip() and not l.strip().startswith("#")]
                for line in lines:
                    self.onecmd(line)
                os.chdir(prevdir)

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

    def push(self, line):
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
                except orerrors.OneringException, exc:
                    logerror(exc.message)
                    traceback.print_exc()
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
        return code.InteractiveConsole.raw_input(self, self.prompt)

    def onecmd(self, line):
        self.push(line)

    def cmdloop(self):
        self.interact()
        self.on_exit()
