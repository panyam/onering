import ipdb
import traceback
import pprint
from collections import defaultdict

class Annotatable(object):
    def __init__(self, annotations = None, docs = ""):
        if annotations is not None:
            assert type(annotations) is Annotations
        self._annotations = annotations or Annotations()
        self.docs = docs or ""

    def set_annotations(self, annotations):
        self._annotations = annotations
        return self

    def set_docs(self, docs):
        self._docs = docs
        return self

    @property
    def annotations(self):
        return self._annotations

    @annotations.setter
    def annotations(self, value): self._annotations = value

    def get_annotation(self, name):
        for annotation in self._annotations:
            if annotation.name == name:
                return annotation
        return None

    def has_annotation(self, name):
        return self.get_annotation(name) is not None

    def copy_from(self, another):
        self._annotations = another._annotations[:]
        self.docs = another.docs

class Annotations(object):
    """
    Keeps track of annotations.
    """
    def __init__(self, annotations = []):
        annotations = annotations or []
        if type(annotations) is Annotations:
            annotations = annotations.all_annotations
        self.all_annotations = annotations

    def __iter__(self):
        return iter(self.all_annotations)

    def add(self, *annotations):
        for a in annotations:
            self.all_annotations.append(a)
        return self

    def has(self, name):
        """
        Returns True if there is atleast one annotation by a given name, otherwise False.
        """
        for a in self.all_annotations:
            if a.name == name:
                return True
        return False

    def get_first(self, name):
        """
        Get the first annotation by a given name.
        """
        for a in self.all_annotations:
            if a.name == name:
                return a
        return None

    def get_all(self, name):
        """
        Get all the annotation by a given name.
        """
        return [annot for annot in self.all_annotations if annot.name == name]

class Annotation(object):
    def __init__(self, fqn, value = None, param_specs = None):
        self.fqn = fqn
        self._value = value
        self._param_specs = defaultdict(list)
        speciter = param_specs or []
        if type(param_specs) is dict:
            speciter = param_specs.iteritems()
        for k,v in speciter:
            assert k not in self._param_specs, "Param %s already exists.  Consider using a list?" % k
            self._param_specs[k] = v

    @property
    def name(self):
        return self.fqn

    @property
    def has_value(self):
        return self._value is not None

    @property
    def has_params(self):
        return self._param_specs is not None and len(self._param_specs) > 0

    def has_param(self, name):
        return name in self._param_specs and len(self._param_specs[name]) > 0

    @property
    def params(self):
        return self._param_specs or {}

    @property
    def value(self):
        if self._value:
            return self._value
        elif self._param_specs:
            return self.params

    def values_of(self, name):
        """
        Return all values of a param
        """
        if name in self._param_specs:
            return self._param_specs[name]
        return None

    def first_value_of(self, name, default_value = None):
        """
        Return the first value of a particular param by name if it exists otherwise false.
        """
        vals = self.values_of(name)
        if vals is not None:
            return vals if type(vals) is not list else vals[0]
        return default_value

    def __repr__(self):
        out = "<Annotation(0x%x), Name: %s" % (id(self), self.fqn)
        if self._value:
            out += ", Value: %s" % str(self._value)
        if self._param_specs:
            out += ", Args: (%s)" % ", ".join(["[%s=%s]" % (x,y) for x,y in self._param_specs.iteritems()])
        out += ">"
        return out
