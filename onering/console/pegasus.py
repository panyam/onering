
import shlex
import ipdb
import runner
from onering.actions import loaders
from utils import logerror

class PegasusCommandRunner(runner.CommandRunner):
    def do_load(self, console, cmd, rest, prev):
        fqn_or_path = rest
        loaders.LoaderActions(console.thering).load_pegasus(fqn_or_path)
        if not console.type_registry.has_type(fqn_or_path):
            ipdb.set_trace()
            logerror("Could not find or load model: %s" % fqn)
