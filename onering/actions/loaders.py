

from collections import defaultdict
import fnmatch
import os, sys, ipdb
from onering import dsl
from onering import resolver
from onering.utils.misc import collect_files
from onering.actions.base import ActionGroup

class LoaderActions(ActionGroup):
    """
    Actions to load models from different different sources.
    """
    def __init__(self, context):
        ActionGroup.__init__(self, context)

    def load_courier(self, fqn_or_path):
        """
        Loads a model denoted by either its name (to be resolved by the schema resolver) or by an absolute path.
        If the parameter has %s in it then the parameter is treated as a (absolute or relative) path, otherwise 
        it is treated as a fully qualified name(fqn).  Once loaded the model is registered with the name specified
        in the model schema.

        **Parameters:**

            fqn_or_path     The FQN or the path to a schema to be loaded.

        **Returns:**
            A tuple of (resolved, unresolved) types that were loaded (or referenced).
        """
        context = self.context
        onering_parser = dsl.parser.Parser(open(fqn_or_path), context, None)

        resolved_types_before = context.type_registry.resolved_types
        unresolved_types_before = context.type_registry.unresolved_types

        resolved_type_names_before = set(context.type_registry.resolved_type_names)
        unresolved_type_names_before = set(context.type_registry.unresolved_type_names)
        self.courier_loader.load(fqn_or_path)
        resolved_type_names_after = set(context.type_registry.resolved_type_names)
        unresolved_type_names_after = set(context.type_registry.unresolved_type_names)

        new_resolved_types = resolved_type_names_after - resolved_type_names_before
        new_unresolved_types = unresolved_type_names_after - unresolved_type_names_before

        return new_resolved_types, new_unresolved_types

    def load_pegasus(self, fqn_or_path):
        """
        Loads a model denoted by either its name (to be resolved by the schema resolver) or by an absolute path.
        If the parameter has %s in it then the parameter is treated as a (absolute or relative) path, otherwise 
        it is treated as a fully qualified name(fqn).  Once loaded the model is registered with the name specified
        in the model schema.

        **Parameters:**

            fqn_or_path     The FQN or the path to a schema to be loaded.
        """
        context = self.context
        pegasus_loader = readers.pegasus.PegasusSchemaLoader(context.type_registry, context.entity_resolver)
        return pegasus_loader.load(fqn_or_path)

    def load_onering_paths(self, paths_or_wildcards):
        """
        Loads one or more onering files.   A onering file could contain models, derivations, 
        transformations, bindings etc.  The path can be a file or a folder (in which case 
        all files with the given extension in the path are loaded).

        **Parameters:**
        paths_or_wildcards  -   One or more files, folders, wildcards pointing to onering files to be loaded.
        """

        import onering.dsl as dsl
        context = self.context

        if type(paths_or_wildcards) in (str, unicode):
            paths_or_wildcards = [paths_or_wildcards]

        schema_paths = []
        for path_or_wildcard in paths_or_wildcards:
            abspath = context.abspath(path_or_wildcard)
            if context.isfile(path_or_wildcard):
                schema_paths.append(abspath)
            elif context.isfile(path_or_wildcard + ".onering"):
                schema_paths.append(abspath + ".onering")
            else:
                dirname = os.path.dirname(abspath)
                if context.isdir(dirname):
                    base_wildcard = os.path.basename(abspath) or "*.onering"
                    for f in collect_files(dirname):
                        if fnmatch.fnmatch(f, base_wildcard):
                            schema_paths.append(f)
                else:
                    raise Exception("Invalid path: %s" % abspath)

        found_entities = {}
        for path in schema_paths:
            print "Loading schema from %s: " % path
            parser = dsl.parser.Parser(open(path), context)
            module = parser.parse()
            found_entities.update(parser.found_entities)
        return found_entities
