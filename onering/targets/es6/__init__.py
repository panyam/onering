
import os
import ipdb
from typelib import annotations as tlannotations
from typelib import core as tlcore
from onering.utils.misc import FQN
from onering.utils.dirutils import open_file_for_writing
from onering.codegen import core as orgencore
from onering.packaging.utils import is_type_entity, is_type_fun_entity, is_fun_entity
from onering.targets import base
import imputils

"""
This module is responsible for all logic and handling around the generation of a 
self contained nodejs package from a package spec.
"""

class Generator(base.Generator):
    def __init__(self, context, package, output_dir):
        base.Generator.__init__(self, context, package, output_dir)

    def open_file(self, filename):
        return File(self, filename)

    def load_template(self, template_name, **extra_globals):
        templ = base.Generator.load_template(self, template_name, **extra_globals)
        templ.globals["gen_constructor"] = make_constructor
        return templ

    def generate(self):
        self._generate_preamble()

        aliases = []
        for fqn,entity in self.package.found_entities.iteritems():
            # send this to a particular file based on its fqn
            filename = imputils.base_filename_for_fqn(self.package, fqn)
            filename = "lib/" + filename;
            outfile = self.ensure_file(filename)

            # Ensure that particular module is declared for use in this file
            outfile.ensure_module(fqn)

            if is_type_entity(entity) and entity.constructor == "typeref":
                # Comeback to aliases at the end
                aliases.append((fqn,entity))
            else:
                self.write_entity(fqn, entity, outfile)
                outfile.write("\n")

        for fqn,alias in aliases:
            # Now write out aliases in which ever file they were found
            filename = imputils.base_filename_for_fqn(self.package, fqn)
            filename = "lib/" + filename;
            outfile = self.ensure_file(filename)
            # TODO: figure out how to write out to aliases and see if they are supported
            # self._write_alias_to_file(fqn, alias, outfile)

        # Close all the files we have open
        self.close_files()

    def _generate_preamble(self):
        """ Generates the package.json for a given package in the output dir."""
        mainfile = self.ensure_file("lib/main.js")
        mainfile.write(self.load_template("es6/main.js.tpl").render()).close()

        indexfile = self.ensure_file("index.js")
        indexfile.write(self.load_template("es6/index.js.tpl").render()).close()

        pkgfile = self.ensure_file("package.json")
        pkgfile.write(self.load_template("es6/package.json.tpl").render()).close()


    def _write_alias_to_file(self, fqn, entity, outfile):
        print "Alias FQN: ", fqn
        resolver_stack = tlcore.ResolverStack(entity.parent, None)
        fqn = FQN(fqn, None)
        value = entity.args[0].type_expr.resolve(resolver_stack)
        outfile.write("exports.%s = %s;\n" % (fqn.fqn, value.fqn))
        outfile.write("%s = exports.%s;\n\n" % (fqn.fqn, fqn.fqn))

    def write_entity(self, fqn, entity, outfile):
        if is_type_entity(entity):
            self._write_model_to_file(fqn, entity, outfile)
        elif is_fun_entity(entity):
            self._write_function_to_file(fqn, entity, outfile)
        elif is_type_fun_entity(entity):
            self._write_typefun_to_file(fqn, entity, outfile)
        else:
            print "No writer found for entity: ", fqn, entity

    def _write_model_to_file(self, fqn, entity, outfile):
        """ Generates the POJO corresponding to the particular module/type entity. """

        # For each record, enum and union that is in the context, generate the ES6 file for it.
        # All type refs that can only be generate at the end
        assert entity.constructor != "typeref"
        print "Generating %s model" % fqn
        if entity.constructor == "record":
            # How to find the template for this typeref?
            templ = self.load_template("es6/class.tpl")
            outfile.write(templ.render(record = TypeViewModel(fqn, entity, self)))
        elif entity.constructor == "enum":
            # How to find the template for this typeref?
            templ = self.load_template("es6/enum.tpl")
            outfile.write(templ.render(enum = TypeViewModel(fqn, entity, self)))
        elif entity.constructor == "union":
            # How to find the template for this typeref?
            templ = self.load_template("es6/union.tpl")
            outfile.write(templ.render(union = TypeViewModel(fqn, entity, self)))

    def _write_function_to_file(self, fqn, entity, outfile):
        """ Generates all required functions. """
        funview = FunViewModel(entity, self)
        outfile.write(funview.render(outfile.importer))

    def _write_typefun_to_file(self, fqn, entity, outfile):
        """ Generates a type function. """
        typefunview = TypeFunViewModel(entity, self)
        outfile.write(typefunview.render(outfile.importer))

class File(base.File):
    """ A file to which a collection of entries are written to. """
    def __init__(self, generator, fname):
        base.File.__init__(self, generator, fname)
        self.ensured_modules = set()
        self.ensured_imports = set()
        self.importer = imputils.Importer(generator.package.current_platform)

    def ensure_import(self, alias, path, submodule = None):
        key = alias + ":" + path + ":" + str(submodule)
        if key not in self.ensured_imports:
            self.ensured_imports.add(key)
            self.write('var %s = require("%s")' % (alias, path))
            if submodule:
                self.write(".%s" % submodule)
            self.write(";\n")

    def ensure_module(self, fqn):
        if fqn in self.ensured_modules: return
        parts = fqn.split(".")[:-1]
        out = ""
        for index,part in enumerate(parts):
            if index > 0: out += "."
            out += part
            if out not in self.ensured_modules:
                if index == 0:
                    self.write("var %s = exports.%s = {}\n" % (out, out))
                else:
                    self.write("%s = {}\n" % out)
            self.ensured_modules.add(out)

    def close(self):
        """ Close the output file. """
        self.write(self.importer.render_imports())
        base.File.close(self)

def make_constructor(typeexpr, resolver_stack, importer):
    """Generates the constructor call for a given type."""
    resolved_type = typeexpr
    while type(resolved_type) is tlcore.Var or type(resolved_type) is tlcore.TypeApp:
        resolved_type = resolved_type.resolve(resolver_stack)
    if type(resolved_type) is not tlcore.Type: ipdb.set_trace()
    assert type(resolved_type) is tlcore.Type
    if resolved_type.name == "map":
        return "{}"
    elif resolved_type.name == "list":
        return "[]"
    else:
        if type(resolved_type) is tlcore.Type:
            if resolved_type.constructor == "literal":
                if resolved_type.name == "any":
                    return "null";
                elif resolved_type.name == "boolean":
                    return "false";
                elif resolved_type.name in ("int", "long"):
                    return "0";
                elif resolved_type.name in ("float", "double"):
                    return "0.0";
                elif resolved_type.name == "string":
                    return '""';
                ipdb.set_trace()
            elif resolved_type.constructor == "record":
                return "new %s()" % importer.ensure(resolved_type.fqn)
        else:
            ipdb.set_trace()
            assert type(resolved_type) is tlcore.TypeParam
    assert False, "Cannot create constructor for invalid type: %s" % repr(resolved_type)

class TypeViewModel(object):
    def __init__(self, fqn, thetype, generator):
        self.generator = generator
        self.thetype = thetype
        self.fqn = fqn = FQN(fqn, None)

class TypeFunViewModel(object):
    def __init__(self, function, generator, resolver_stack = None):
        if resolver_stack == None:
            resolver_stack = tlcore.ResolverStack(function.parent, None)
        self.resolver_stack = resolver_stack.push(function)
        self.generator = generator
        self.function = function

    def render(self, importer):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.generator.load_template("es6/typefun.tpl", importer = importer)
        templ.globals["resolver_stack"] = self.resolver_stack
        return templ.render(view = self, function = self.function, resolver_stack = self.resolver_stack)


class FunViewModel(object):
    def __init__(self, function, generator, resolver_stack = None):
        print "Fun Value: ", function
        assert not function.is_type_fun
        if resolver_stack == None:
            resolver_stack = tlcore.ResolverStack(function.parent, None)
        self.resolver_stack = resolver_stack.push(function)
        self.generator = generator
        self.function = function
        self.instructions, self.symtable = orgencore.generate_ir_for_function(function, self.resolver_stack)

    def render(self, importer):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.generator.load_template("es6/function.tpl", importer = importer, resolver_stack = self.resolver_stack)
        return templ.render(view = self, function = self.function, resolver_stack = self.resolver_stack)
