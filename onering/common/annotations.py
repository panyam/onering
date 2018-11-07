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
    def annotations(self): return self._annotations

    @annotations.setter
    def annotations(self, value): self._annotations = value

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

    def has(self, fqn):
        """
        Returns True if there is atleast one annotation by a given fqn, otherwise False.
        """
        for a in self.all_annotations:
            if a.fqn == fqn:
                return True
        return False

    def get_first(self, fqn):
        """
        Get the first annotation by a given fqn.
        """
        for a in self.all_annotations:
            if a.fqn == fqn:
                return a
        return None

    def get_all(self, fqn):
        """
        Get all the annotation by a given fqn.
        """
        return [annot for annot in self.all_annotations if annot.fqn == fqn]

class Annotation(object):
    def __init__(self, fqn, value = None):
        self._fqn = fqn
        self._value = value

    @property
    def fqn(self): return self._fqn

    @property
    def value(self): return self._value

    def __repr__(self):
        out = "<Annotation(0x%x), Name: %s" % (id(self), self.fqn)
        if self._value:
            out += ", Value: %s" % str(self._value)
        out += ">"
        return out
