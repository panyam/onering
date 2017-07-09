
import os
import json
from ipdb import set_trace
from typelib import annotations as tlannotations
from typelib import core as tlcore
from typelib import ext as tlext
from onering.utils.misc import FQN
from onering.utils.dirutils import open_file_for_writing
from onering.codegen import desugar2 as desugar
from onering.codegen import symtable, ir
from onering.packaging.utils import is_type_entity, is_type_fun_entity, is_fun_entity
from onering.targets import base
from onering.targets import common as orgencommon
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

    def template_loaded(self, templ):
        """ Called after a template has been loaded. """
        base.Generator.template_loaded(self, templ)
        templ.globals["make_constructor"] = make_constructor
        templ.globals["render_expr"] = self.render_expr
        templ.globals["render_type"] = self.render_type
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

            if is_type_entity(entity) and entity.category == tlcore.TypeCategory.ALIAS_TYPE:
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
        fqn = FQN(fqn, None)
        value = entity.args[0].type_expr.resolve()
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
        assert entity.category != "typeref"
        typeview = TypeViewModel(fqn, entity, self)
        outfile.write(typeview.render(outfile.importer))

    def _write_function_to_file(self, fqn, entity, outfile):
        """ Generates all required functions. """
        funview = FunViewModel(entity, self, entity.fun_type)
        outfile.write(funview.render(outfile.importer))

    def _write_typefun_to_file(self, fqn, entity, outfile):
        """ Generates a type function. """
        typefunview = TypeFunViewModel(entity, self)
        outfile.write(typefunview.render(outfile.importer))

    def render_expr(self, expr):
        """ Renders an expression onto the current template. """
        self.renderers = {
            tlcore.FunApp: "render_funapp",
            tlcore.Var: "render_var",

            tlext.ExprList: "render_exprlist",
            tlext.Literal: "render_literal",
            tlext.Assignment: "render_assignment",
            tlext.ListExpr: "render_listexpr",
            tlext.DictExpr: "render_dictexpr",
            tlext.TupleExpr: "render_listexpr",
        }
        rend_func = self.renderers[type(expr)]
        template = """
            {%% import "es6/macros.tpl" as macros %%}
            {{macros.%s (expr)}}
        """ % rend_func
        return self.load_template_from_string(template).render(expr = expr)

    def render_type(self, thetype):
        """ Renders an expression onto the current template. """
        self.renderers = {
            tlcore.Type: "render_basic_type",
        }
        rend_func = self.renderers[type(thetype)]
        template = """
            {%% import "es6/macros.tpl" as macros %%}
            {{macros.%s (thetype)}}
        """ % rend_func
        set_trace()
        return self.load_template_from_string(template).render(thetype = thetype)

    def render_symtable(self, symtable):
        out = ""
        if symtable.declarations:
            out = "var " + ", ".join(varname for varname,_ in symtable.declarations)
        return out

    def render_typeapp(self, expr):
        set_trace()
        pass

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

class TypeViewModel(object):
    def __init__(self, fqn, thetype, generator):
        self.generator = generator
        self.thetype = thetype
        self.fqn = fqn = FQN(fqn, None)

    def render(self, importer):
        print "Generating %s model" % self.fqn.fqn
        templ = self.generator.load_template("es6/%s.tpl" % self.thetype.tag)
        templ.globals["importer"] = importer
        return templ.render(**{self.thetype.tag: self})

class TypeFunViewModel(object):
    def __init__(self, typefun, generator = None):
        self.generator = generator
        self.typefun = typefun
        if not issubclass(typefun.return_typearg.type_expr.__class__, tlcore.Type):
            set_trace()
            assert False, "Type function expressions can only be types."
        self.child_view = TypeViewModel("", self.typefun.return_typearg.type_expr, generator)

    def render(self, importer, with_variable = True):
        print "Generating Fun: %s" % self.typefun.fqn
        templ = self.generator.load_template("es6/typefun.tpl", importer = importer)
        return templ.render(view = self, typefun = self.typefun, with_variable = with_variable)


class FunViewModel(object):
    def __init__(self, function, generator, fun_type):
        print "Fun Value: ", function
        self.function = function
        self.generator = generator
        self._symtable = None
        self.real_fun_type = self.function.fun_type
        if self.function.fun_type.is_type_function:
            self.real_fun_type = self.function.fun_type.return_typearg.type_expr
        self.return_typearg = self.real_fun_type.return_typearg
        if self.return_typearg.type_expr == tlcore.VoidType:
            self.return_typearg = None

    def render(self, importer, with_variable = True):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.generator.load_template("es6/function.tpl", importer = importer)
        return templ.render(view = self, function = self.function, with_variable = with_variable)


def make_constructor(typeexpr, importer):
    """Generates the constructor call for a given type."""
    resolved_type = typeexpr
    while type(resolved_type) is tlcore.TypeRef:
        resolved_type = resolved_type.resolve()
    assert issubclass(resolved_type.__class__, tlcore.Type)
    if resolved_type.fqn == "map":
        return "{}"
    elif resolved_type.fqn == "list":
        return "[]"
    elif type(resolved_type) is tlcore.Type:
        if resolved_type.category == "literal":
            if resolved_type.fqn == "any":
                return "null";
            elif resolved_type.fqn == "boolean":
                return "false";
            elif resolved_type.fqn in ("int", "long"):
                return "0";
            elif resolved_type.fqn in ("float", "double"):
                return "0.0";
            elif resolved_type.fqn == "string":
                return '""';
            set_trace()
        elif resolved_type.tag == "record":
            return "new %s()" % importer.ensure(resolved_type.fqn)
    elif type(resolved_type) is tlcore.TypeApp:
        type_fun = resolved_type.args[0].resolve().type_expr
        type_args = [arg.type_expr.resolve() for arg in resolved_type.args[1:]]
        return "new (%s(%s))()" % (importer.ensure(type_fun.fqn), ", ".join(arg.name for arg in type_args))
    set_trace()
    assert False, "Cannot create constructor for invalid type: %s" % repr(resolved_type)
