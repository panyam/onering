
import os, sys
import ipdb
from onering.loaders import resolver
from onering import utils as orutils
from onering.actions.base import ActionGroup

def jar_collector(context, path):
    if context.isdir(path):
        return [ resolver.ZipFilePathEntityResolver(jar_file, "pegasus")
                        for jar_file in orutils.collect_jars(context.abspath(path)) ]
    elif context.isfile(path):
        return [ resolver.ZipFilePathEntityResolver(context.abspath(path), "pegasus") ]
    else:
        raise Exception("Invalid jar path: %s" % path)

def dir_collector(context, path):
    if context.isdir(path):
        return [resolver.FilePathEntityResolver(context.abspath(path))]
    elif context.isfile(path):
        raise Exception("Cannot add a single file as a schema path")
    else:
        raise Exception("Invalid path: %s" % path)
    return []

class JarActions(ActionGroup):
    """
    Actions to manage directories in which jars (that contain archived pegasus schemas) are
    added, removed or searched for.
    """
    def __init__(self, context):
        ActionGroup.__init__(self, context)

    def add(self, *paths):
        """
        Add a jar file or directory contain jars that contain schemas (structured in a 
        hierarchy reflecting the fully qualified names).

        **Parameters**:
            *paths  One or more jar files or directories contains jar files.
        """
        context = self.context
        for entry in paths:
            entry = entry.strip()
            for resolver in jar_collector(context, entry):
                context.entity_resolver.add_resolver(resolver)

    def remove(self, *paths):
        """
        Remove one or more jar files or directories containing jar files that contain 
        schemas (structured in a hierarchy reflecting the fully qualified names).

        **Parameters:**
            paths   One or more jar files or jar dirs to remove.
        """
        context = self.context
        for entry in paths:
            entry = entry.strip()
            entry = context.abspath(entry)
            for resolver in jar_collector(context, entry):
                context.entity_resolver.remove_resolver(resolver)


class DirActions(ActionGroup):
    """
    Actions to manage directories in which directories (that contain archived pegasus schemas) 
    are added, removed or searched for.
    """
    def __init__(self, context):
        ActionGroup.__init__(self, context)

    def add(self, *paths):
        """
        Add a directory that contains schemas (structured in a hierarchy reflecting 
        the fully qualified names).

        **Parameters**:
            paths  One or more directories containing schemas.
        """
        context = self.context
        for entry in paths:
            entry = entry.strip()
            for resolver in dir_collector(context, entry):
                context.entity_resolver.add_resolver(resolver)

    def remove(self, *paths):
        """
        Remove one or more directories containing schemas (structured in a 
        hierarchy reflecting the fully qualified names).

        **Parameters:**
            paths   One or more paths containing schemas.
        """
        context = self.context
        for entry in paths:
            entry = entry.strip()
            entry = context.abspath(entry)
            for resolver in dir_collector(context, entry):
                context.entity_resolver.remove_resolver(resolver)

class TemplateActions(ActionGroup):
    """
    Manage directories in which templates are searched for, added or removed from.
    """
    def __init__(self, context):
        ActionGroup.__init__(self, context)

    def add(self, *paths):
        """
        Add the root folder containing templates.

        **Parameters:**
        *paths      One or more folders containing templates.
        """
        context = self.context
        for path in paths:
            entry = path.strip()
            if entry:
                entry = context.abspath(entry)
                if entry not in context.template_dirs:
                    context.template_loader.template_dirs.append(entry)

    def remove(self, *paths):
        """
        Remove a directory containing templates.

        **Parameters:**
            *paths      Directories containing templates to be removed.
        """
        context = self.context
        for entry in paths:
            entry = entry.strip()
            if entry in context.template_dirs:
                del context.template_loader.template_dirs[context.template_dirs.index(entry)]
