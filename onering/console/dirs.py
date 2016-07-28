
import os, sys
import ipdb
import runner
from onering import resolver
from onering import utils as orutils
from utils import logerror

class JarsCommandRunner(runner.CommandRunner):
    """
    Manage directories in which jars (the contain archived schemas) are searched for.

    Usage:
        list                List the directories in which jars are searched for.
        add     <jar/dir>   Add one or more space seperated jar files or directory containing jars.
        remove  <dir/dir>   Remove one or more space seperated jar files or directory containing jars.
    """

    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    @classmethod
    def collector(cls, path):
        if os.path.isdir(path):
            return [resolver.ZipFilePathEntityResolver(jar_file, "pegasus") for jar_file in orutils.collect_jars(path)]
        elif os.path.isfile(path):
            return [ resolver.ZipFilePathEntityResolver(path, "pegasus") ]
        else:
            logerror("Invalid jar path: %s" % path)

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the jar files that will be searched when resolving/loading new entities.
        """
        resolvers = [str(x) for x in console.entity_resolver.resolvers if type(x) == resolver.ZipFilePathEntityResolver]
        print "\n".join(resolvers)

    def do_add(self, console, cmd, rest, prev = None):
        """
        Add a jar file or directory contain jars that contain schemas (structured in a hierarchy reflecting the fully qualified names).
        """
        entry = (rest or "").strip()
        for resolver in JarsCommandRunner.collector(entry):
            console.entity_resolver.add_resolver(resolver)

    def do_remove(self, console, cmd, rest, prev = None):
        """
        Remove a jar file or directory contain jars that contain schemas (structured in a hierarchy reflecting the fully qualified names).
        """
        entry = (rest or "").strip()
        for resolver in JarsCommandRunner.collector(entry):
            console.entity_resolver.remove_resolver(resolver)


class DirsCommandRunner(runner.CommandRunner):
    """
    Manage directories in which schemas are searched for.

    Usage:
        list                List the directories in which schemas are searched for.
        add         <dir>   Add one or more space seperated directories containing schemas.
        remove/rm   <dir>   Remove one or more space seperated schema directory schemas.
    """
    @property
    def aliases(self):
        return { "ls": "list", "rm": "remove" }

    @classmethod
    def collector(cls, path):
        if os.path.isdir(path):
            return [resolver.FilePathEntityResolver(path)]
        elif os.path.isfile(path):
            logerror("Cannot add a single file as a schema path")
        else:
            logerror("Invalid path: %s" % path)
        return []

    def do_list(self, console, cmd, rest, prev = None):
        """
        List the folders that will be searched when resolving/loading new entities.
        """
        resolvers = [str(x) for x in console.entity_resolver.resolvers if type(x) == resolver.FilePathEntityResolver]
        print "\n".join(resolvers)

    def do_add(self, console, cmd, rest, prev = None):
        """
        Add a directory containing schemas (structured in a hierarchy reflecting the fully qualified names).
        """
        entry = (rest or "").strip()
        for resolver in DirsCommandRunner.collector(entry):
            console.entity_resolver.add_resolver(resolver)

    def do_remove(self, console, cmd, rest, prev = None):
        """
        Remove a directory containing schemas (structured in a hierarchy reflecting the fully qualified names).
        """
        entry = (rest or "").strip()
        for resolver in DirsCommandRunner.collector(entry):
            console.entity_resolver.remove_resolver(resolver)
