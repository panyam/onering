
from jinja2 import Environment, PackageLoader
import pkgutil
import ipdb

def load_template_from_path(template_path, extensions = None):
    default_extensions = [ "jinja2.ext.do", "jinja2.ext.with_" ]
    if extensions:
        extensions.extend(default_extensions)
    else:
        extensions = default_extensions
    kwargs = dict(trim_blocks = True,
                  lstrip_blocks = True,
                  extensions = extensions)
    #if not template_path.startswith("/"): kwargs["loader"] = PackageLoader("onering", "data/templates")
    env = Environment(**kwargs)
    if template_path[0] == "/":
        return env.from_string(open(template_path).read())
    else:
        return env.from_string(pkgutil.get_data("onering", "data/templates/" + template_path))
