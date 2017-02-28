
import os, sys
import ipdb
import runner
from onering import resolver
from onering import utils as orutils
from onering.actions import dirs as diractions
from utils import logerror

class JarsCommandRunner(runner.CommandRunner):
    """
    Manage directories in which jars (that contain archived pegasus schemas) are searched for.
    """
    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the jar files that will be searched when resolving/loading new entities.

        Usage:
            list                List the directories in which jars are searched for.
        """
        resolvers = [str(x) for x in console.entity_resolver.resolvers if type(x) == resolver.ZipFilePathEntityResolver]
        print "\n".join(resolvers)

    def do_add(self, console, cmd, rest, prev = None):
        return diractions.JarActions(console.thering).add(rest)

    def do_remove(self, console, cmd, rest, prev = None):
        return diractions.JarActions(console.thering).remove(rest)

class DirsCommandRunner(runner.CommandRunner):
    """
    Manage directories in which schemas are searched for.
    """
    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the folders that will be searched when resolving/loading new entities.

        Usage:
            list                List the directories in which schemas are searched for.
        """
        resolvers = [str(x) for x in console.entity_resolver.resolvers if type(x) == resolver.FilePathEntityResolver]
        print "\n".join(resolvers)

    def do_add(self, console, cmd, rest, prev = None):
        return diractions.DirActions(console.thering).add(rest)

    def do_remove(self, console, cmd, rest, prev = None):
        return diractions.DirActions(console.thering).remove(rest)

class TemplatesCommandRunner(runner.CommandRunner):
    """
    Manage directories in which templates are searched for.
    """
    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the folders that will be searched when resolving/loading templates.
        """
        print "\n".join(console.thering.template_dirs)

    def do_add(self, console, cmd, rest, prev = None):
        return diractions.TemplateActions(console.thering).add(rest)

    def do_remove(self, console, cmd, rest, prev = None):
        return diractions.TemplateActions(console.thering).remove(rest)
