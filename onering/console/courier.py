
import shlex
import ipdb
import runner
from onering.action import loaders

class CourierCommandRunner(runner.CommandRunner):
    def do_load(self, console, cmd, fqn_or_path, prev):
        new_resolved_types, new_unresolved_types = loaders.LoaderActions(console.context).load_courier(fqn_or_path)
        console.type_registry.print_types(list(new_resolved_types.union(new_unresolved_types)))
