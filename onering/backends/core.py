import ipdb
import os
import sys

from onering import utils
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
                    'field_name': fname, 
                    'field_type': ftype,
                    'annotations': tlannotations.Annotations(annots)
                } for ((fname, ftype), annots) in zip(thetype.children, thetype._child_annotations)]

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
        self.transformers = [TransformerViewModel(t,self, backend) for t in tgroup.all_transformers]


class TransformerViewModel(object):
    def __init__(self, transformer, tgroup, backend):
        self.backend = backend
        self.name = transformer.fqn
        self.tgroup = tgroup
        self.src_name,self.src_namespace,self.src_fqn = utils.normalize_name_and_ns(transformer.src_fqn, "")
        self.dest_name,self.dest_namespace,self.dest_fqn = utils.normalize_name_and_ns(transformer.dest_fqn, "")

    @property
    def rendered_string(self):
        ipdb.set_trace()
        templ = self.backend.load_template(self.backend.backend_annotation.first_value_of("template") or "transformers/java/default_transformer")
        out = templ.render(transformer = self, tgroup = self.tgroup, backend = self.backend)
        return out

