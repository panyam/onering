
import os
import json
from ipdb import set_trace
from typecube import annotations as tlannotations
from typecube import core as tlcore
from typecube import ext as tlext
from onering.utils.misc import FQN
from onering.utils.dirutils import open_file_for_writing
from onering.codegen import symtable, ir
from onering.packaging.utils import is_type_entity, is_typeop_entity, is_fun_entity
from onering.targets import base
from onering.targets import common as orgencommon
import imputils

"""
This module is responsible for all logic and handling around the generation of a 
self contained nodejs package from a package spec.
"""

class Generator(base.Generator):
    def open_file(self, filename):
        return File(self, filename)

    def filename_for_entity(self, fqn, entity):
        filename = imputils.base_filename_for_fqn(self.package, fqn)
        filename = "lib/" + filename;
        return filename

    def generate(self):
        self._generate_preamble()

        aliases = []
        for fqn,entity in self.package.found_entities.iteritems():
            # send this to a particular file based on its fqn
            filename = self.filename_for_entity(fqn, entity)
            outfile, just_opened = self.ensure_file(filename)

            # Ensure that particular module is declared for use in this file
            outfile.ensure_module(fqn)

            if is_type_entity(entity) and entity.is_alias_type:
                # Comeback to aliases at the end
                aliases.append((fqn,entity))
            else:
                self.write_entity(fqn, entity, outfile)
                outfile.write("\n")

        for fqn,alias in aliases:
            # Now write out aliases in which ever file they were found
            filename = imputils.base_filename_for_fqn(self.package, fqn)
            filename = "lib/" + filename;
            outfile, just_opened = self.ensure_file(filename)
            # TODO: figure out how to write out to aliases and see if they are supported
            # self._write_alias_to_file(fqn, alias, outfile)

        self._generate_main()

        # Close all the files we have open
        self.close_files()

    def _generate_main(self):
        gen_files = []
        for f in self._allfiles.iterkeys():
            if not f.endswith(".js"): continue
            if not f.startswith("lib/"): continue
            if f == "lib/index.js": continue
            gen_files.append({
                'basename': f.replace("lib/", "./").replace(".js",""),
                'export_name': os.path.basename(f).replace(".js","")
            })
        mainfile, just_opened = self.ensure_file("lib/main.js")
        mainfile.write(mainfile.load_template("es6/main.js.tpl").render(gen_files = gen_files)).close()

    def _generate_preamble(self):
        """ Generates the package.json for a given package in the output dir."""
        indexfile, just_opened = self.ensure_file("index.js")
        indexfile.write(indexfile.load_template("es6/index.js.tpl").render()).close()

        pkgfile, just_opened = self.ensure_file("package.json")
        pkgfile.write(pkgfile.load_template("es6/package.json.tpl").render()).close()


    def _write_alias_to_file(self, fqn, entity, outfile):
        print "Alias FQN: ", fqn
        fqn = FQN(fqn, None)
        value = entity.args[0].expr.resolve()
        outfile.write("exports.%s = %s;\n" % (fqn.fqn, value.fqn))
        outfile.write("%s = exports.%s;\n\n" % (fqn.fqn, fqn.fqn))

    def write_entity(self, fqn, entity, outfile):
        if is_type_entity(entity):
            self._write_model_to_file(fqn, entity, outfile)
        elif is_fun_entity(entity):
            self._write_function_to_file(fqn, entity, outfile)
        elif is_typeop_entity(entity):
            self._write_typeop_to_file(fqn, entity, outfile)
        else:
            print "No writer found for entity: ", fqn, entity

    def _write_model_to_file(self, fqn, entity, outfile):
        """ Generates the POJO corresponding to the particular module/type entity. """
        assert not entity.is_alias_type
        outfile.write(TypeViewModel(fqn, entity, outfile).render())

    def _write_function_to_file(self, fqn, entity, outfile):
        """ Generates all required functions. """
        outfile.write(FunViewModel(entity, entity.fun_type, outfile).render())

    def _write_typeop_to_file(self, fqn, entity, outfile):
        """ Generates a type function. """
        outfile.write(TypeOpViewModel(entity, outfile).render())

class File(base.File):
    """ A file to which a collection of entries are written to. """
    def __init__(self, generator, fname):
        base.File.__init__(self, generator, fname)
        self.ensured_modules = set()
        self.ensured_imports = set()
        self.importer = imputils.Importer(generator.package.current_platform)

    def template_loaded(self, templ):
        """ Called after a template has been loaded. """
        base.File.template_loaded(self, templ)
        templ.globals["make_constructor"] = make_constructor
        templ.globals["render_expr"] = self.render_expr
        templ.globals["render_type"] = self.render_type
        return templ

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

    def render_type(self, thetype, importer):
        """ Renders an expression onto the current template. """
        self.renderers = {
            tlcore.Type: "render_basic_type",
            tlcore.ProductType: "render_record",
            tlcore.SumType: "render_union",
        }
        rend_func = self.renderers[type(thetype)]
        template = """
            {%%- import "es6/macros.tpl" as macros -%%} {{macros.%s (thetype)}}
        """ % rend_func
        templ = self.load_template_from_string(template)
        templ.globals["importer"] = importer
        return templ.render(thetype = thetype)

    def render_symtable(self, symtable):
        out = ""
        if symtable.declarations:
            out = "var " + ", ".join(varname for varname,_ in symtable.declarations)
        return out

class TypeViewModel(object):
    def __init__(self, fqn, thetype, outfile):
        self.outfile = outfile
        self.thetype = thetype
        self.fqn = fqn = FQN(fqn, None)

    def render(self):
        print "Generating %s model" % self.fqn.fqn
        templ = self.outfile.load_template("es6/%s.tpl" % self.thetype.tag)
        return templ.render(**{self.thetype.tag: self})

class TypeOpViewModel(object):
    def __init__(self, typeop, outfile):
        self.typeop = typeop
        self.outfile = outfile
        self.child_view = TypeViewModel("", self.typeop.expr, outfile)

    def render(self):
        print "Generating Fun: %s" % self.typeop.fqn
        templ = self.outfile.load_template("es6/typeop.tpl")
        return templ.render(view = self, typeop = self.typeop)


class FunViewModel(object):
    def __init__(self, function, fun_type, outfile):
        print "Fun Value: ", function
        self.function = function
        self.outfile = outfile
        self._symtable = None
        self.return_typearg = self.function.fun_type.return_typearg
        if self.return_typearg and self.return_typearg.expr == tlcore.VoidType:
            self.return_typearg = None

    def render(self):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.outfile.load_template("es6/function.tpl")
        return templ.render(view = self, function = self.function)

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
    elif resolved_type.is_atomic_type:
        if resolved_type.fqn == "any":
            return "null"
        elif resolved_type.fqn == "boolean":
            return "false"
        elif resolved_type.fqn in ("int", "long"):
            return "0"
        elif resolved_type.fqn in ("float", "double"):
            return "0.0"
        elif resolved_type.fqn == "string":
            return '""'
    elif issubclass(resolved_type.__class__, tlcore.ContainerType) and resolved_type.tag == "record":
        return "new %s()" % importer.ensure(resolved_type.fqn)
    elif type(resolved_type) is tlcore.TypeApp:
        typeop = resolved_type.expr.resolve()
        typeargs = [arg.resolve() for arg in resolved_type.args]
        out = "new (%s(%s))()" % (importer.ensure(typeop.fqn), ", ".join(importer.ensure(arg.fqn) for arg in typeargs))
        return out
    set_trace()
    assert False, "Cannot create constructor for invalid type: %s" % repr(resolved_type)
