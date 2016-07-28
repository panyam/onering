
import shlex
import ipdb
import runner
from onering import readers
from utils import logerror

class PegasusCommandRunner(runner.CommandRunner):
    def __init__(self):
        self.pegasus_loader = None

    def do_load(self, console, cmd, rest, prev):
        """
        Loads a model denoted by either its name (to be resolved by the schema resolver) or by an absolute path.
        If the parameter has %s in it then the parameter is treated as a (absolute or relative) path, otherwise 
        it is treated as a fully qualified name(fqn).  Once loaded the model is registered with the name specified
        in the model schema.

        Usage:

            load  fqn_or_path
        """
        if not self.pegasus_loader:
            self.pegasus_loader = readers.pegasus.PegasusSchemaLoader(console.type_registry, console.entity_resolver)

        fqn_or_path = rest
        self.pegasus_loader.load(fqn_or_path)

        if not console.type_registry.has_type(fqn_or_path):
            ipdb.set_trace()
            logerror("Could not find or load model: %s" % fqn)
