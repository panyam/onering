
import typelib
from typelib.utils import *
import os
from itertools import ifilter

def collect_files(root_dir):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for name in files:
            full_path = os.path.join(root, name)
            yield full_path

def collect_files_by_extension(root_dir, ext):
    return ifilter(lambda path: path.endswith("." + ext) and os.path.isfile(path), collect_files(root_dir))

def collect_jars(root_dir):
    def is_model_jar(name):
        return name.find("data-template") > 0 and name.find("SNAPSHOT") < 0 and name.endswith(".jar")
    return ifilter(is_model_jar, collect_files(root_dir))

class ResolutionStatus(object):
    def __init__(self):
        self._resolved = False
        self._resolving = False

    @property
    def succeeded(self):
        return self._resolved

    @property
    def in_progress(self):
        return self._resolving

    def _mark_in_progress(self, value):
        self._resolving = value

    def _mark_resolved(self, value):
        self._resolved = value

    def perform_once(self, action):
        result = None
        if not self._resolved:
            if self._resolving:
                from onering import errors
                raise errors.OneringException("Action already in progress.   Possible circular dependency found")

            self._resolving = True

            result = action()

            self._resolving = False
            self._resolved = True
        return result

from optparse import Option
class ListOption(Option):
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extend":
            lvalue = value.split(",")
            values.ensure_value(dest, []).extend(lvalue)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)
