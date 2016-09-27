
import os, sys
import ipdb
import runner
from onering import resolver
from onering import utils as orutils
from utils import logerror

class JarsCommandRunner(runner.CommandRunner):
    """
    Manage directories in which jars (that contain archived pegasus schemas) are searched for.
    """

    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    @classmethod
    def collector(cls, console, path):
        if console.isdir(path):
            return [resolver.ZipFilePathEntityResolver(jar_file, "pegasus") for jar_file in orutils.collect_jars(console.abspath(path))]
        elif console.isfile(path):
            return [ resolver.ZipFilePathEntityResolver(console.abspath(path), "pegasus") ]
        else:
            logerror("Invalid jar path: %s" % path)

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the jar files that will be searched when resolving/loading new entities.

        Usage:
            list                List the directories in which jars are searched for.
        """
        resolvers = [str(x) for x in console.entity_resolver.resolvers if type(x) == resolver.ZipFilePathEntityResolver]
        print "\n".join(resolvers)

    def do_add(self, console, cmd, rest, prev = None):
        """
        Add a jar file or directory contain jars that contain schemas (structured in a hierarchy reflecting the fully qualified names).

        Usage:
            add     <jar/dir>   Add one or more space seperated jar files or directory containing jars.
        """
        entry = (rest or "").strip()
        for resolver in JarsCommandRunner.collector(console, entry):
            console.entity_resolver.add_resolver(resolver)

    def do_remove(self, console, cmd, rest, prev = None):
        """
        Remove a jar file or directory contain jars that contain schemas (structured in a hierarchy reflecting the fully qualified names).

        Usage:
            remove  <dir/dir>   Remove one or more space seperated jar files or directory containing jars.
        """
        entry = (rest or "").strip()
        entry = console.abspath(entry)
        for resolver in JarsCommandRunner.collector(console, entry):
            console.entity_resolver.remove_resolver(resolver)


class DirsCommandRunner(runner.CommandRunner):
    """
    Manage directories in which schemas are searched for.
    """
    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    @classmethod
    def collector(cls, console, path):
        if console.isdir(path):
            return [resolver.FilePathEntityResolver(console.abspath(path))]
        elif console.isfile(path):
            logerror("Cannot add a single file as a schema path")
        else:
            logerror("Invalid path: %s" % path)
        return []

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the folders that will be searched when resolving/loading new entities.

        Usage:
            list                List the directories in which schemas are searched for.
        """
        resolvers = [str(x) for x in console.entity_resolver.resolvers if type(x) == resolver.FilePathEntityResolver]
        print "\n".join(resolvers)

    def do_add(self, console, cmd, rest, prev = None):
        """
        Add a directory containing schemas (structured in a hierarchy reflecting the fully qualified names).

        Usage:
            add         <dir>   Add one or more space seperated directories containing schemas.
        """
        entry = (rest or "").strip()
        for resolver in DirsCommandRunner.collector(console, entry):
            console.entity_resolver.add_resolver(resolver)

    def do_remove(self, console, cmd, rest, prev = None):
        """
        Remove a directory containing schemas (structured in a hierarchy reflecting the fully qualified names).

        Usage:
            remove/rm   <dir>   Remove one or more space seperated schema directory schemas.
        """
        entry = (rest or "").strip()
        for resolver in DirsCommandRunner.collector(console, entry):
            console.entity_resolver.remove_resolver(resolver)

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
        """
        Add a directory containing schemas (structured in a hierarchy reflecting the fully qualified names).

        Usage:
            add         <dir>   Add one or more space seperated template directories
        """
        entry = (rest or "").strip()
        if entry:
            entry = console.abspath(entry)
            if entry not in console.thering.template_dirs:
                console.thering.template_loader.template_dirs.append(entry)

    def do_remove(self, console, cmd, rest, prev = None):
        """
        Remove a directory containing schemas (structured in a hierarchy reflecting the fully qualified names).

        Usage:
            remove/rm   <dir>   Remove one or more space seperated template directories.
        """
        entry = (rest or "").strip()
        if entry in console.thering.template_dirs:
            del console.thering.template_loader.template_dirs[console.thering.template_dirs.index(entry)]
