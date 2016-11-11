import ipdb
import os
import sys

from onering import utils
from onering.generator.symtable import SymbolTable
from onering.generator import core as orgencore
from typelib import annotations as tlannotations
from jinja2 import nodes
from jinja2.ext import Extension, contextfunction

class TypeViewModel(object):
    def __init__(self, backend, type_name, thetype, context, backend_annotation):
        self.backend = backend
        self.context = context
        self.backend_annotations = backend_annotation
        n,ns,fqn = utils.FQN(type_name, "").parts
        self.thetype = thetype
        if backend_annotation.has_param("namespace"):
            ns = backend_annotation.first_value_of("namespace")
            fqn = ".".join([ns, n])
        self.name = n
        self.namespace = ns
        self.import_types = []
        self.annotations = tlannotations.Annotations(thetype.annotations)
        self.fields =  [ TypeArgViewModel(arg.name, arg.typeref, tlannotations.Annotations(arg.annotations)) for arg in thetype.args ]

class TypeArgViewModel(object):
    def __init__(self, field_name, field_type, annotations):
        self.field_name = field_name
        self.field_type = field_type
        self.annotations = annotations

class TransformerGroupViewModel(object):
    def __init__(self, backend, tgroup, context, backend_annotation):
        self.backend = backend
        self.context = context
        self.backend_annotations = backend_annotation
        n,ns,fqn = utils.FQN(tgroup.fqn, "").parts
        self.tgroup = tgroup
        if backend_annotation.has_param("namespace"):
            ns = backend_annotation.first_value_of("namespace")
            fqn = ".".join([ns, n])
        self.name = n
        self.namespace = ns
        self.import_types = []
        self.annotations = tlannotations.Annotations(tgroup.annotations)
        self.transformers = [TransformerViewModel(t, self, backend) for t in tgroup.all_transformers]


class TransformerViewModel(object):
    def __init__(self, transformer, tgroupvm, backend):
        self.backend = backend
        self.context = tgroupvm.context
        self.transformer = transformer
        self.tgroupvm = tgroupvm
        self.name = transformer.fqn
        self.instructions, self.symtable = orgencore.generate_ir_for_transformer(transformer, self.context)
        src_fqns = [utils.FQN(fqn, "").fqn for fqn in transformer.src_fqns]
        self.src_variables = zip(src_fqns, transformer.src_varnames)
        self.dest_varname = transformer.dest_varname
        self.dest_name,self.dest_namespace,self.dest_fqn = utils.FQN(transformer.dest_fqn, "").parts
        self.all_statements = [StatementViewModel(stmt, self, backend) for stmt in  transformer.all_statements]

        self.deduped_statements = {}
        for stmt in self.all_statements:
            self.deduped_statements[str(stmt.statement.target_variable.normalized_field_path)] = stmt

    def render(self):
        template_name = "transformers/%s/to_mutable_pojo" % self.backend.platform_name
        for annotation in self.transformer.annotations:
            if annotation.name == "onering.backend" and annotation.first_value_of("platform") == self.backend.platform_name:
                template_name = annotation.first_value_of("template") or template_name
                break
        templ = self.backend.load_template(template_name )
        out = templ.render(transformer = self, tgroup = self.tgroupvm, backend = self.backend)
        return out


class StatementViewModel(object):
    def __init__(self, statement, transformervm, backend):
        self.statement = statement
        self.transformervm = transformervm
        self.backend = backend

