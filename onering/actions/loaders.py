

from collections import defaultdict
import fnmatch
import os, sys
import importlib
from ipdb import set_trace
from onering import dsl
from onering.loaders import resolver
from onering.utils.misc import collect_files
from onering.actions.base import ActionGroup

class LoaderActions(ActionGroup):
    """
    Actions to load models from different different sources.
    """
    def __init__(self, context):
        ActionGroup.__init__(self, context)

    def load_entries(self, entries):
        """ Entry point for loading either a single file, a wild card of files, multiple files or
        even invoking a custom loader to do domain specific loading of schemas into onering.

        *Parameters:*

            entries     -   Can be a single entry or a list of entries. Each entry can be:
                            * A single path of the onering schema file (or a wild card of files) to load.   
                              The type of loader invoked would depend on the extension fo the file.   
                                .avsc for Avro loaders,
                                .pdsc for pegasus loaders,
                                .thrift for thrift loaders,
                                and the rest using onering loaders.
                            * A dictionary pointing to a custom loader.  The dictionary must have a 
                              single "loader" parameter/key which is a string value of the FQN 
                              pointing to the Loader class that can process the entries.  The loader class
                              is imported, instantiated with the dictionary as its arguments and will
                              have its "load" method called with the context as its arguments.
        """
        found_entities = {}
        context = self.context
        if type(entries) is not list:
            entries = [entries]

        # Collect all entries first by normalizing the wild cards
        for entry in entries:
            if type(entry) in (str, unicode):
                # Load by file extensions
                paths_or_wildcards = entry
                if context.isfile(entry):
                    found_entities.update(self.load_file(entry))
                else:
                    abspath = context.abspath(entry)
                    dirname = os.path.dirname(abspath)
                    if not context.isdir(dirname):
                        raise OneringException("Invalid path: %s" % abspath)
                    base_wildcard = os.path.basename(abspath) or "*.onering"
                    for f in collect_files(dirname):
                        if fnmatch.fnmatch(f, base_wildcard):
                            found_entities.update(self.load_file(f))
            elif not issubclass(entry.__class__, dict):
                raise OneringException("Entry can be a string or a dictionary")
            else:
                loader_class_parts = entry["loader"].split(".")
                basemod, classname = ".".join(loader_class_parts[:-1]), loader_class_parts[-1]
                loader_class = getattr(importlib.import_module(basemod), classname)
                entry_args = entry.get("args",[])
                entry_kwargs = entry.get("kwargs",{})
                loader = loader_class(context, *entry_args, **entry_kwargs)
                found = loader.load()
                found_entities.update(found)
        return found_entities

    def load_file(self, path):
        print "Loading schema from %s: " % path
        basepath, ext = os.path.splitext(path)
        if ext.lower() == ".pdsc":
            return readers.pegasus.Loader(self.context).load(fqn_or_path)
        elif ext.lower() == ".avsc":
            return readers.avro.Loader(self.context).load(fqn_or_path)
        elif ext.lower() == ".thrift":
            return readers.thrift.Loader(self.context).load(fqn_or_path)
        else:   # onering
            parser = dsl.parser.Parser(open(path), self.context)
            parser.parse()
            return parser.found_entities

