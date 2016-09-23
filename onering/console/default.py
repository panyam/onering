
from __future__ import absolute_import
import os
import json
import shlex
import ipdb
from onering.console import runner, dirs, pegasus, courier, orc, platform
from onering.utils import split_list_at, parse_line_dict
from onering.console.utils import logerror
from onering.generator import utils as orgenutils

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
            # "pegasus": pegasus.PegasusCommandRunner(),
            "dirs": dirs.DirsCommandRunner(),
            "templates": dirs.TemplatesCommandRunner(),
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
        console.curdir = rest.strip()
        print "Dir: ", os.curdir

    def do_pwd(self, console, cmd, rest, prev):
        """
        Prints out the current working directory.
        """
        print 
        print self.curdir()
        print 

    def do_gen(self, console, cmd, rest, prev):
        """
        Generate code or schemas for given types and derivations.

        Usage:
            gen     <types>
            gen     <types>      with    <platform> <template>

            <types>     Is a list of (space seperated) wild cards
            <platform>  If a platform is specified then the generated output is for the particular platform.
                        If the platform is not specified then the platform specified in the type's 
                        "onering.backend" annotation is used.
                        If this annotation is not specified then the default platform is used. Otherwise
                        an error is thrown.
            <template>  Same for templates, specifed -> annotation -> default
        """
        # Couple of more things to do here!
        # First, this should also pick up all derivations

        wildcards = []
        wildcards = [r.split(",") for r in rest.split(" ")]
        wildcards = filter(lambda x:x, reduce(lambda x,y:x+y, wildcards))
        wildcards, _, param_args = split_list_at(lambda x:x == "with", wildcards)
        target_platform = param_args[0] if len(param_args) > 0 else None
        target_template = param_args[1] if len(param_args) > 1 else None

        source_types = console.thering.type_registry.types_for_wildcards(wildcards)
        source_derivations = console.thering.derivations_for_wildcards(wildcards)

        # Awwwwright resolutions succeeded so now generate them!
        for source_fqn in source_types:
            source_type = console.type_registry.get_type(source_fqn)
            orgenutils.generate_schemas(source_type, console.thering, target_platform, target_template)

        for deriv in source_derivations:
            source_type = console.type_registry.get_type(deriv)
            orgenutils.generate_schemas(source_type, console.thering, target_platform, target_template)

    def do_gent(self, console, cmd, rest, prev):
        """
        Generate code for transformers

        Usage:
            gen     <types>
            gen     <types>      with    <platform> <template>

            <types>     Is a list of (space seperated) wild cards
            <platform>  If a platform is specified then the generated output is for the particular platform.
                        If the platform is not specified then the platform specified in the type's 
                        "onering.backend" annotation is used.
                        If this annotation is not specified then the default platform is used. Otherwise
                        an error is thrown.
            <template>  Same for templates, specifed -> annotation -> default
        """
        # Couple of more things to do here!
        # First, this should also pick up all derivations

        wildcards = []
        wildcards = [r.split(",") for r in rest.split(" ")]
        wildcards = filter(lambda x:x, reduce(lambda x,y:x+y, wildcards))
        wildcards, _, param_args = split_list_at(lambda x:x == "with", wildcards)
        target_platform = param_args[0] if len(param_args) > 0 else None
        target_template = param_args[1] if len(param_args) > 1 else None

        transformer_groups = console.thering.transformer_groups_for_wildcards(wildcards)

        # Awwwwright resolutions succeeded so now generate them!
        for tgfqn in transformer_groups:
            tg = console.thering.get_transformer_group(tgfqn)
            orgenutils.generate_transformers(tg, console.thering, target_platform, target_template)

