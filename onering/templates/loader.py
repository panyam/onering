
from __future__ import absolute_import
from jinja2 import BaseLoader, TemplateNotFound, StrictUndefined
from jinja2 import Environment, PackageLoader
import pkgutil
import os
from os.path import join, exists, getmtime
import ipdb
from . import utils

class TemplateLoader(BaseLoader):
    """
    Responsible for loading templates given a name.
    """
    def __init__(self, template_dirs = None, default_extension = ".tpl"):
        self.template_dirs = template_dirs or []
        self.template_extension = default_extension or ""

    def get_source(self, environment, template_name):
        final_path = template_name
        if not template_name.startswith("/"):
            for tdir in self.template_dirs:
                full_path = os.path.join(tdir, template_name)
                if os.path.isfile(full_path):
                    final_path = full_path
                    break
                else:
                    full_path = os.path.join(tdir, template_name + self.template_extension)
                    if os.path.isfile(full_path):
                        final_path = full_path
                        break
            else:
                source = pkgutil.get_data("onering", "data/templates/" + template_name).decode('utf-8')
                return source, final_path, lambda: True

        with file(final_path) as f:
            source = f.read().decode('utf-8')
        return source, final_path, lambda: mtime == getmtime(final_path)

    def load_template(self, name, extensions = None):
        default_extensions = [ "jinja2.ext.do", "jinja2.ext.with_" ]
        if extensions:
            extensions.extend(default_extensions)
        else:
            extensions = default_extensions
        kwargs = dict(trim_blocks = True,
                      lstrip_blocks = True,
                      undefined = StrictUndefined,
                      extensions = extensions)
        #if not template_path.startswith("/"): kwargs["loader"] = PackageLoader("onering", "data/templates")
        env = Environment(**kwargs)
        env.loader = self
        return env.get_template(name)
