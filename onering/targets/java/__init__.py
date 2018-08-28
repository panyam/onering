
import os
import json
from ipdb import set_trace
from onering.utils.misc import FQN
from onering.utils.dirutils import open_file_for_writing
from onering.codegen import symtable, ir
from onering.packaging.utils import is_type_entity, is_typefun_entity, is_fun_entity
from onering.targets import base
from onering.targets import common as orgencommon
import imputils

"""
This module is responsible for all logic and handling around the generation of a 
self contained java package from a package spec.
"""

class Generator(base.Generator):
    def open_file(self, filename):
        return File(self, filename)

    def filename_for_entity(self, fqn, entity):
        return os.path.join(*(["src"] + fqn.split("."))) + ".java"

    def generate(self):
        aliases = []
        for fqn,entity in self.package.found_entities.iteritems():
            # send this to a particular file based on its fqn
            filename = self.filename_for_entity(fqn, entity)
            outfile, just_opened = self.ensure_file(filename)

            if is_type_entity(entity) and entity.is_alias_type:
                # Comeback to aliases at the end
                aliases.append((fqn,entity))
            else:
                self.write_entity(fqn, entity, outfile)
                outfile.write("\n")

        for fqn,alias in aliases:
            print "Found alias: ", fqn,alias.fqn
            set_trace()
            # Now write out aliases in which ever file they were found
            # filename = imputils.base_filename_for_fqn(self.package, fqn)
            # filename = "lib/" + filename;
            # outfile, just_opened = self.ensure_file(filename)
            # TODO: figure out how to write out to aliases and see if they are supported
            # self._write_alias_to_file(fqn, alias, outfile)

        # Close all the files we have open
        self.close_files()


    def file_opened(self, filename, file):
        """ Called when a file has just been opened for writing. This can be used to 
        write any preambles required onto the file."""
        if not filename.endswith(".java"): return

        filename = filename[:-len(".java")]
        filename = filename[len("src/"):]
        namespace = ".".join(filename.split(os.path.sep))
        file.write("package %s;\n" % namespace)
        file.write("\n")
        file.write("#INSERT_IMPORTS\n")
        file.write("\n")

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
        elif is_typefun_entity(entity):
            self._write_typefun_to_file(fqn, entity, outfile)
        else:
            print "No writer found for entity: ", fqn, entity

    def _write_model_to_file(self, fqn, entity, outfile):
        """ Generates the POJO corresponding to the particular module/type entity. """
        assert not entity.is_alias_type
        outfile.write(TypeViewModel(fqn, entity, outfile).render())

    def _write_function_to_file(self, fqn, entity, outfile):
        """ Generates all required functions. """
        outfile.write(FunViewModel(entity, entity.fun_type, outfile).render())

    def _write_typefun_to_file(self, fqn, entity, outfile):
        """ Generates a type function. """
        outfile.write(TypeFunViewModel(entity, outfile).render())

class File(base.File):
    """ A file to which a collection of entries are written to. """
    def __init__(self, generator, fname):
        base.File.__init__(self, generator, fname)
        self.importer = imputils.Importer(generator.package.current_platform)

    def template_loaded(self, templ):
        """ Called after a template has been loaded. """
        base.File.template_loaded(self, templ)
        templ.globals["signature"] = signature
        templ.globals["render_expr"] = self.render_expr
        templ.globals["render_type"] = self.render_type
        return templ

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
            {%% import "java/macros.tpl" as macros %%}
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
            {%%- import "java/macros.tpl" as macros -%%} {{macros.%s (thetype)}}
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
        templ = self.outfile.load_template("java/%s.tpl" % self.thetype.tag)
        return templ.render(**{self.thetype.tag: self})

class TypeFunViewModel(object):
    def __init__(self, typefun, outfile):
        self.typefun = typefun
        self.outfile = outfile
        self.child_view = TypeViewModel("", self.typefun.expr, outfile)

    def render(self):
        print "Generating Fun: %s" % self.typefun.fqn
        templ = self.outfile.load_template("java/typefun.tpl")
        return templ.render(view = self, typefun = self.typefun)


class FunViewModel(object):
    def __init__(self, function, fun_type, outfile):
        print "Fun Value: ", function
        self.function = function
        self.outfile = outfile
        self._symtable = None
        self.real_fun_type = self.function.fun_type
        if self.function.fun_type.is_type_fun:
            self.real_fun_type = self.real_fun_type.expr
        self.return_typearg = self.real_fun_type.return_typearg
        if self.return_typearg and self.return_typearg.expr == tlcore.VoidType:
            self.return_typearg = None

    def render(self):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.outfile.load_template("java/function.tpl")
        return templ.render(view = self, function = self.function)


def signature(typeexpr, importer):
    """Generates the constructor call for a given type."""
    resolved_type = typeexpr
    while type(resolved_type) is tlcore.TypeRef:
        resolved_type = resolved_type.resolve()
    assert issubclass(resolved_type.__class__, tlcore.Type)
    if resolved_type.fqn == "map":
        return importer.ensure("java.awt.Map")
    elif resolved_type.fqn == "list":
        return importer.ensure("java.awt.List")
    elif resolved_type.is_atomic_type:
        if resolved_type.fqn == "any":
            return "Object"
        elif resolved_type.fqn in ("boolean", "int", "long", "float", "double", "string"):
            return resolved_type.fqn
    elif issubclass(resolved_type.__class__, tlcore.ContainerType):
        return importer.ensure(resolved_type.fqn)
    elif type(resolved_type) is tlcore.TypeApp:
        typefun = resolved_type.expr.resolve()
        typeargs = [arg.resolve() for arg in resolved_type.args]
        return "%s<%s>" % (signature(typefun, importer), ", ".join(arg.name for arg in typeargs))
    elif resolved_type.is_typeref:
        return signature(resolved_type.resolve(), importer)
    elif resolved_type.is_alias_type:
        return signature(resolved_type.target_type, importer)
    set_trace()
    assert False, "Cannot create constructor for invalid type: %s" % repr(resolved_type)
