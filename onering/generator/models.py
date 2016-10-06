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
        n,ns,fqn = utils.normalize_name_and_ns(type_name, "")
        self.thetype = thetype
        if backend_annotation.has_param("namespace"):
            ns = backend_annotation.first_value_of("namespace")
            fqn = ".".join([ns, n])
        self.name = n
        self.namespace = ns
        self.import_types = []
        self.annotations = tlannotations.Annotations(thetype.annotations)
        self.fields =  [ {
                    'field_name': arg.name, 
                    'field_type': arg.typeref,
                    'annotations': tlannotations.Annotations(arg.annotations) } for arg in thetype.args ]

class TransformerGroupViewModel(object):
    def __init__(self, backend, tgroup, context, backend_annotation):
        self.backend = backend
        self.context = context
        self.backend_annotations = backend_annotation
        n,ns,fqn = utils.normalize_name_and_ns(tgroup.fqn, "")
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
        self.tgroupvm = tgroupvm
        self.name = transformer.fqn
        self.instructions, self.symtable = orgencore.generate_ir_for_transformer(transformer, self.context)
        self.src_name,self.src_namespace,self.src_fqn = utils.normalize_name_and_ns(transformer.src_fqn, "")
        self.src_varname = transformer.src_varname
        self.dest_varname = transformer.dest_varname
        self.dest_name,self.dest_namespace,self.dest_fqn = utils.normalize_name_and_ns(transformer.dest_fqn, "")
        self.all_statements = [StatementViewModel(stmt, self, backend) for stmt in  transformer.all_statements]

    def render(self):
        templ = self.backend.load_template(self.backend.backend_annotation.first_value_of("template") or "transformers/java/default_transformer")
        out = templ.render(transformer = self, tgroup = self.tgroupvm, backend = self.backend)
        return out


class StatementViewModel(object):
    def __init__(self, statement, transformervm, backend):
        self.statement = statement
        self.transformervm = transformervm
        self.backend = backend

