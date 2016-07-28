
import shlex
import ipdb
import runner
from onering import readers
from onering import dsl

class CourierCommandRunner(runner.CommandRunner):
    def __init__(self):
        self.onering_parser = None

    def do_load(self, console, cmd, fqn_or_path, prev):
        """
        Loads a model denoted by either its name (to be resolved by the schema resolver) or by an absolute path.
        If the parameter has %s in it then the parameter is treated as a (absolute or relative) path, otherwise 
        it is treated as a fully qualified name(fqn).  Once loaded the model is registered with the name specified
        in the model schema.

        Usage:

            load  fqn_or_path
        """
        if not self.onering_parser:
            self.onering_parser = dsl.parser.Parser(open(fqn_or_path), console.type_registry, None)

        resolved_types_before = console.type_registry.resolved_types
        unresolved_types_before = console.type_registry.unresolved_types

        ipdb.set_trace()

        resolved_type_names_before = set(console.type_registry.resolved_type_names)
        unresolved_type_names_before = set(console.type_registry.unresolved_type_names)
        self.courier_loader.load(fqn_or_path)
        resolved_type_names_after = set(console.type_registry.resolved_type_names)
        unresolved_type_names_after = set(console.type_registry.unresolved_type_names)

        new_resolved_types = resolved_type_names_after - resolved_type_names_before
        new_unresolved_types = unresolved_type_names_after - unresolved_type_names_before

        console.type_registry.print_types(list(new_resolved_types.union(new_unresolved_types)))
