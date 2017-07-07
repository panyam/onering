
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
        self.renderer = ExpressionRenderer(self)

    def open_file(self, filename):
        return File(self, filename)

    def load_template(self, template_name, **extra_globals):
        templ = base.Generator.load_template(self, template_name, **extra_globals)
        templ.globals["gen_constructor"] = make_constructor
        templ.globals["render_expr"] = self.render_expr
        # templ.globals["render_type"] = self.render_type
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

            if is_type_entity(entity) and entity.category == "typeref":
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
        assert entity.category != "typeref"
        print "Generating %s model" % fqn
        if entity.category == "record":
            # How to find the template for this typeref?
            templ = self.load_template("es6/class.tpl")
            outfile.write(templ.render(record = TypeViewModel(fqn, entity, self)))
        elif entity.category == "enum":
            # How to find the template for this typeref?
            templ = self.load_template("es6/enum.tpl")
            outfile.write(templ.render(enum = TypeViewModel(fqn, entity, self)))
        elif entity.category == "union":
            # How to find the template for this typeref?
            templ = self.load_template("es6/union.tpl")
            outfile.write(templ.render(union = TypeViewModel(fqn, entity, self)))

    def _write_function_to_file(self, fqn, entity, outfile):
        """ Generates all required functions. """
        funview = FunViewModel(entity, self)
        return
        outfile.write(funview.render(outfile.importer))

    def _write_typefun_to_file(self, fqn, entity, outfile):
        """ Generates a type function. """
        typefunview = TypeFunViewModel(entity, self)
        return
        outfile.write(typefunview.render(outfile.importer))

    def render_expr(self, expr, resolver_stack):
        """ Renders an expression onto the current template. """
        self.renderer.render(expr, resolver_stack)

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
    if type(resolved_type) is not tlcore.Type:
        set_trace()
    assert type(resolved_type) is tlcore.Type
    if resolved_type.name == "map":
        return "{}"
    elif resolved_type.name == "list":
        return "[]"
    else:
        if type(resolved_type) is tlcore.Type:
            if resolved_type.category == "literal":
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
                set_trace()
            elif resolved_type.category == "record":
                return "new %s()" % importer.ensure(resolved_type.fqn)
        else:
            set_trace()
            assert type(resolved_type) is tlcore.TypeParam
    assert False, "Cannot create constructor for invalid type: %s" % repr(resolved_type)

class TypeViewModel(object):
    def __init__(self, fqn, thetype, generator):
        self.generator = generator
        self.thetype = thetype
        self.fqn = fqn = FQN(fqn, None)

class TypeFunViewModel(object):
    def __init__(self, typefun, generator, resolver_stack = None):
        if resolver_stack == None:
            resolver_stack = tlcore.ResolverStack(typefun.parent, None)
        self.resolver_stack = resolver_stack.push(typefun)
        self.generator = generator
        self.typefun = typefun
        # if type(typefun.expr) is tlcore.Fun: self.child_view = FunViewModel(self.typefun.expr, generator, self.resolver_stack)
        if not issubclass(typefun.result_typearg.type_expr.__class__, tlcore.Type):
            set_trace()
            assert False, "Type function expressions can only be types."
        self.child_view = TypeViewModel("", self.typefun.result_typearg.type_expr, generator)

    def render(self, importer, with_variable = True):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.generator.load_template("es6/typefun.tpl", importer = importer)
        templ.globals["resolver_stack"] = self.resolver_stack
        return templ.render(view = self, function = self.function, resolver_stack = self.resolver_stack, with_variable = with_variable)


class FunViewModel(object):
    def __init__(self, function, generator, resolver_stack = None):
        print "Fun Value: ", function
        if resolver_stack == None:
            resolver_stack = tlcore.ResolverStack(function.parent, None)
        self.resolver_stack = resolver_stack.push(function)
        self.generator = generator
        # self.function, self.symtable = desugar.transform_function(function, self.resolver_stack)
        self.function, self.symtable = function, None

    def render(self, importer, with_variable = True):
        print "Generating Fun: %s" % self.function.fqn
        templ = self.generator.load_template("es6/function.tpl", importer = importer, resolver_stack = self.resolver_stack)
        return templ.render(view = self, function = self.function, resolver_stack = self.resolver_stack, with_variable = with_variable)


class ExpressionRenderer(object):
    def __init__(self, generator):
        self.generator = generator
        self.renderers = {
            tlcore.Var: self.render_var,
            tlcore.Fun: self.render_fun,
            tlcore.FunApp: self.render_funapp,
            tlcore.TypeApp: self.render_typeapp,
            tlext.Literal: self.render_literal,
            tlext.ExprList: self.render_exprlist,
            tlext.IfExpr: self.render_ifexpr,
            tlext.NewExpr: self.render_newexpr,
            tlext.ListExpr: self.render_listexpr,
            tlext.DictExpr: self.render_dictexpr,
            tlext.TupleExpr: self.render_tupleexpr,
            tlext.Assignment: self.render_assignment,
            symtable.SymbolTable: self.render_symtable,
            symtable.Register: self.render_register,
            ir.ContainsExpr: self.render_contains,
            ir.NotExpr: self.render_not,
            ir.GetterExpr: self.render_getter,
            ir.SetterExpr: self.render_setter,
        }

    def render(self, expr, resolver_stack):
        return self.renderers[type(expr)](expr, resolver_stack)

    def render_exprlist(self, expr, resolver_stack):
        return ";\n".join(self.render(e, resolver_stack) for e in expr.children)

    def render_ifexpr(self, expr, resolver_stack):
        out = ""
        for index,(cond,body) in enumerate(expr.cases):
            if index > 0:
                out += "else "
            out += "if ("
            out += self.render(cond, resolver_stack)
            out += ") { "
            out += self.render(body, resolver_stack)
            out += "}"
        if expr.default_expr:
            out += "else {"
            out += self.render(expr.default_expr, resolver_stack)
            out += "}"
        return out

    def render_newexpr(self, expr, resolver_stack):
        pass

    def render_listexpr(self, expr, resolver_stack):
        return "[%s]" % ", ".join(map(self.render_expr, expr.values))

    def render_tupleexpr(self, expr, resolver_stack):
        return "[%s]" % ", ".join(map(self.render_expr, expr.values))

    def render_dictexpr(self, expr, resolver_stack):
        keyvalues = ["%s: %s" % (self.render(key, resolver_stack), self.render(value, resolver_stack)) for (key,value) in izip(expr.keys, expr.values)]
        return "{%s}" % ", ".join(keyvalues)

    def render_symtable(self, symtable, resolver_stack):
        out = ""
        if symtable.declarations:
            out = "var " + ", ".join(varname for varname,_ in symtable.declarations)
        return out

    def render_register(self, register, resolver_stack):
        assert register.label
        return register.label

    def render_assignment(self, expr, resolver_stack):
        rhs = self.render(expr.expr, resolver_stack)
        lhs = ""
        ipdb.set_trace()
        first = expr.target_variable.field_path.get(0)
        if expr.target_variable.field_path.length == 1:
            lhs = first
        else:
            lhs = """ensure_field_path(%s.__class__, "%s").%s""" % (
                        expr.target_variable.field_path.poptail(),
                        expr.target_variable.field_path.get(-1))
        return "%s = %s" % (lhs, rhs)

    def render_fun(self, expr, resolver_stack):
        set_trace()
        pass

    def render_funapp(self, funapp, resolver_stack):
        out = ""
        if funapp.func_expr.fqn:
            out = funapp.func_expr.fqn
        else:
            out = self.render(funapp.func_expr, resolver_stack)
        return out + "(%s)" % ", ".join(map(self.render, funapp.func_args))

    def render_typeapp(self, expr, resolver_stack):
        set_trace()
        pass

    def render_literal(self, expr, resolver_stack):
        set_trace()
        pass

    def render_var(self, var, resolver_stack):
        first, rest = var.field_path.pop()
        set_trace()
        return """get_field_path(%s, %s.__class__, "%s").%s""" % (first, "something", rest)

    def render_contains(self, expr, resolver_stack):
        return self.render(expr.source_expr, resolver_stack) + ".has%s" + orgencommon.camel_case(expr.field_name)

    def render_not(self, expr, resolver_stack):
        return "!" + self.render(expr.source_expr, resolver_stack)

    def render_getter(self, expr, resolver_stack):
        return self.render(expr.source_expr, resolver_stack) + "." + expr.field_name

    def render_setter(self, expr, resolver_stack):
        return self.render(expr.target_expr, resolver_stack) + "." + expr.field_name + " = " + self.render(expr.target_expr, resolver_stack)
