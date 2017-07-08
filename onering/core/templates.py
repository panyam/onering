
from __future__ import absolute_import
import pkgutil
import os
from os.path import join, exists, getmtime
import ipdb
from jinja2 import BaseLoader, TemplateNotFound, StrictUndefined
from jinja2 import Environment, PackageLoader


class TemplateLoader(BaseLoader):
    """
    Responsible for loading templates given a name.
    """
    def __init__(self, template_dirs = None, default_extension = ".tpl", parent_loader = None):
        self.template_dirs = template_dirs or []
        self.template_extension = default_extension or ""
        self.parent_loader = parent_loader

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
                # See if parent can return it
                if self.parent_loader:
                    return self.parent_loader.get_source(environment, template_name)
                else:
                    source = pkgutil.get_data("onering", "data/templates/" + template_name).decode('utf-8')
                    return source, final_path, lambda: True

        with file(final_path) as f:
            source = f.read().decode('utf-8')
        return source, final_path, lambda: mtime == getmtime(final_path)

    def get_env(self, extensions = None):
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
        return env

    def load_from_file(self, name, extensions = None):
        env = self.get_env(extensions)
        return initialise_template(env.get_template(name))

    def load_from_string(self, template_string, extensions = None):
        env = self.get_env(extensions)
        return initialise_template(env.from_string(template_string))

def debug_print(*text):
    print "".join(map(str, list(text)))
    return ''

def camel_case(value):
    if value is None: ipdb.set_trace()
    return value[0].upper() + value[1:]

def initialise_template(templ):
    templ.globals["camel_case"] = camel_case
    templ.globals["debug"] = debug_print
    templ.globals["map"] = map
    templ.globals["str"] = str
    templ.globals["type"] = type
    templ.globals["filter"] = filter
    return templ
