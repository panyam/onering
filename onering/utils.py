
from typelib.utils import *
import pkgutil
import ipdb
import os
from itertools import ifilter

def load_template(template_path, extensions = None):
    from jinja2 import Environment, PackageLoader
    default_extensions = [ "jinja2.ext.do", "jinja2.ext.with_" ]
    if extensions:
        extensions.extend(default_extensions)
    else:
        extensions = default_extensions
    kwargs = dict(trim_blocks = True,
                  lstrip_blocks = True,
                  extensions = extensions)
    if not template_path.startswith("/"):
        kwargs["loader"] = PackageLoader("onering", "templates")
    env = Environment(**kwargs)
    if not template_path.startswith("templates/"):
        template_path = "templates/" + template_path
    # ipdb.set_trace() ; return env.get_template(template_path)
    return env.from_string(pkgutil.get_data("onering", template_path))

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

def analyse_multiproduct(mp_dir):
    """
    Given the path to a multiproduct, analysis the models in the MP if it contains a Mainifest 
    listing the transformers
    """
    pass

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
