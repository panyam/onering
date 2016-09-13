
import json
import shlex
import fnmatch
import ipdb
import runner, dirs, pegasus, courier, orc, platform
from utils import logerror

class DefaultCommandRunner(runner.CommandRunner):
    @property
    def aliases(self):
        return { "peg": "pegasus",
                 "orc": "onering" }

    @property
    def children(self):
        return {
            "onering": orc.OneringCommandRunner(),
            "platform": platform.PlatformCommandRunner(),
            "pegasus": pegasus.PegasusCommandRunner(),
            "courier": courier.CourierCommandRunner(),
            "dirs": dirs.DirsCommandRunner(),
            "jars": dirs.JarsCommandRunner()
        }

    def do_reset(self, console, cmd, rest, prev):
        """
        Usage: reset

        Resets the OneRing state and clears out all types and field graphs.
        """
        console.reset()

    def do_load(self, console, cmd, rest, prev):
        """
        Loads a script denoted by either its name (to be resolved by the schema resolver) or by an absolute path.
        If the parameter has SLASHES in it then the parameter is treated as a (absolute or relative) path, 
        otherwise it is treated as a fully qualified name(fqn).

        Options:
            fqn_or_path     FQN or path of the script to be loaded
        """
        script = rest.strip()
        if not script:
            return logerror("load command requires a script file to be loaded and executed")
        console.load_script(script)

    def do_loadt(self, console, cmd, rest, prev):
        """
        Loads an instance transformer given either its name (to be resolved by the schema resolver) or by an 
        absolute path.

        If the parameter has %s in it then the parameter is treated as a (absolute or relative) path, otherwise 
        it is treated as a fully qualified name(fqn).  Once loaded the instance transformer is registered with the 
        name specified in the model schema.

        Usage:

            loadit fqn_or_path
        """
        console.thering.load_instance_transformer(rest.strip())

    def do_set(self, console, cmd, rest, prev):
        """
        Set the value of particular configuration variables.

        Supported configs are:

            output_dir  -   The directory to which all models, DAOs and transformers are written to.
        """
        lexer = shlex.shlex(rest)
        key = lexer.next()
        value = lexer.next()
        if key == "output_dir":
            onering.output_path = value.strip()

    def do_cd(self, console, cmd, rest, prev):
        """
        Changes the current working directory to a given directory.  This is useful to set the base path
        when specifying relative paths in loading schemas/transformers/scripts.
        """
        os.chdir(os.path.abspath(rest.strip()))

    def do_pwd(self, console, cmd, rest, prev):
        """
        Prints out the current working directory.
        """
        print 
        print self.curdir()
        print 

    def do_dumpf(self, console, cmd, rest, prev):
        """
        Dumps out one or more fields in the field graph to standard output.   If not names are provided then all fields are printed.

        Options:
            <field1> <field2> <field3>  Print the field dependencies in field graph for the given fields.
                                        If no fields are provided then all fields are printed.
        """
        print 
        print 
        print 
        print "=" * 80
        print 
        print 
        print 
        lexer = shlex.shlex(rest)
        try:
            lexer.quotes = "."
            names = list(lexer)
            console.thering.field_graph.print_graph(names)
        except StopIteration, si:
            pass

    def do_dumps(self, console, cmd, rest, prev):
        """
        Dumps out one or more schemas to standard output.   If not names are provided then all schemas are printed.

        Options:
            <name1> <name2> <namen>     Print the given schemas with the given fully qualified names.  
                                        If no schemas provided then all schemas are printed.
        """
        lexer = shlex.shlex(rest)
        lexer.quotes = "."
        names = list(lexer)
        print 
        print 
        print 
        print "=" * 80
        print 
        print 
        print 
        ipdb.set_trace()
        console.type_registry.print_types(names)

    def do_gen(self, console, cmd, rest, prev):
        """
        Generate code or schemas for given types, derivations or transformers.

        Usage:
            gen     <types>
            gen     <types>      with    <platforms>

            <types>     Is a list of (space seperated) wild cards
            <platforms> If a list of (space seperated) platforms are specified then the generated output is 
                        based on the particular platform.  
                        If platforms are not specified then the default platform is used.
                        See the platform command on how to register platforms and templates.
        """

        # Couple of more things to do here!
        # First, this should also pick up all derivations

        wildcards = [r.split(",") for r in rest.split(" ")]
        wildcards = filter(lambda x:x, reduce(lambda x,y:x+y, wildcards))
        target_platforms = []
        if "with" in wildcards:
            ind = rest.index("with")
            wildcards, target_platforms = wildcards[:ind], windcards[ind+1]

        if not target_platforms:
            if console.thering.default_platform:
                target_platforms = [ console.thering.default_platform ]
            else:
                return logerror("Please specify a platform or set a default platform")

        source_types = set()
        source_derivations = set()

        for tw in wildcards:
            # First go through all resolved types
            for (fqn,t) in console.thering.type_registry.resolved_types:
                if fnmatch.fnmatch(fqn, tw):
                    source_types.add(fqn)

            # Now resolve all derivations
            for derivation in console.thering.all_derivations:
                if fnmatch.fnmatch(derivation.fqn, tw):
                    derivation.resolve(console.type_registry, None)
                    source_derivations.add(derivation.fqn)

        # Awwwwright resolutions succeeded so now generate them!
        template_name = 
        for platform in target_platforms:
            print "Generating types for platform: %s" % tbend
        ipdb.set_trace()

    def do_resolve(self, console, cmd, rest, prev):
        """
        Usage: resolve

        Resolves field and type dependencies with the currently available types.
        """
        console.type_registry.resolve_types()
