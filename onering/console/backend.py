

import shlex
import ipdb
import runner
from onering import readers
from utils import logerror

class BackendCommandRunner(runner.CommandRunner):
    def do_set(self, console, cmd, rest, prev):
        """
        Sets an alias for a particular backend so that a backend alias could be used instead of its fully
        qualified name/path.   Backend aliases are CASE INSENSITIVE.

        Usage:

            backend     set     alias       fqn
        """
        comps = [r.strip() for r in rest.split(" ") if r.strip()]
        if len(comps) != 2:
            do_man(self, console, cmd, rest, prev)
        else:
            console.thering.backend_aliases[comps[0]] = comps[1]

    def do_list(self, console, cmd, rest, prev):
        """
        List all backend aliases
        """
        print "Backend aliases:"
        print "----------------"
        for a,v in console.thering.backend_aliases.iteritems():
            print "%10s   ->    %s" % (a,v)
