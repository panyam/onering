
from __future__ import absolute_import
from ipdb import set_trace
import pkgutil
from onering.utils import dirutils
import onering.typing.context

class World(object):
    """ The onering world is where all the actors live and interact with one another. """
    def __init__(self):
        self.dirpointer = dirutils.DirPointer()
        self.packages = {}

        self.typing_context = onering.typing.context.Context()

        from onering.loaders import resolver
        self.entity_resolver = resolver.EntityResolver()

        from onering.utils import templates
        self.template_loader = templates.TemplateLoader()

    def load_template(self, template_name):
        return self.template_loader.load_template(template_name)

    def ensure_package(self, package_name, package_spec_path = None):
        if package_name not in self.packages:
            return self.load_package(package_spec_path)
        return self.packages[package_name]

    def load_package(self, package_or_path):
        package = package_or_path
        if type(package) is str:
            from onering.packaging import packages
            package = packages.Package(package_or_path)

        # Now check if it exists already
        if package.name not in self.packages:
            package.load_entities(self)
            self.packages[package.name] = package
        return self.packages[package.name]
