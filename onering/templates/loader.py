
from __future__ import absolute_import
from jinja2 import Environment, PackageLoader
import pkgutil
import os
import ipdb
from . import utils

class TemplateLoader(object):
    """
    Responsible for loading templates given a name.
    """
    def __init__(self, template_dirs = None, default_extension = ".tpl"):
        self.template_dirs = template_dirs or []
        self.template_extension = default_extension or ""


    def load_template(self, name):
        for tdir in self.template_dirs:
            full_path = os.path.join(tdir, name)
            if os.path.isfile(full_path):
                return utils.load_template_from_path(full_path)
            full_path = os.path.join(tdir, name + self.template_extension)
            if os.path.isfile(full_path):
                return utils.load_template_from_path(full_path)
        return utils.load_template_from_path(name)
