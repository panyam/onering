

import shlex
import ipdb
import runner
from onering import readers
from utils import logerror

class PlatformCommandRunner(runner.CommandRunner):
    def do_set(self, console, cmd, rest, prev):
        """
        Sets an alias for a particular platform so that a platform alias could be used instead of its fully
        qualified name/path.   Platform aliases are CASE INSENSITIVE.

        Usage:

            platform     set     alias       fqn
        """
        comps = [r.strip() for r in rest.split(" ") if r.strip()]
        if len(comps) != 2:
            do_man(self, console, cmd, rest, prev)
        else:
            console.thering.platform_aliases[comps[0]] = comps[1]

    def do_list(self, console, cmd, rest, prev):
        """
        List all platform aliases
        """
        print "Platform aliases:"
        print "----------------"
        for a,v in console.thering.platform_aliases.iteritems():
            print "%10s   ->    %s" % (a,v)

    def do_default(self, console, cmd, rest, prev):
        """
        Sets the default platform
        """
        rest = rest.strip()
        if rest:
            aliases = console.thering.platform_aliases
            if rest not in aliases:
                print "Invalid Platform.  Must be one of: [%s]" % ", ".join(aliases.keys())
            else:
                console.thering.default_platform = rest
        print "Default Platform: ", console.thering.default_platform or "<Not Set>"
