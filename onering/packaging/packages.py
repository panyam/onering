from __future__ import absolute_import
from ipdb import set_trace
import os
import glob, fnmatch
import importlib
from onering.utils import dirutils, misc
from onering.actions import LoaderActions
from onering.core import templates as tplloader

class PlatformConfig(object):
    """ Platform specific configs.  """

    """ Name of the platform """
    name = None

    """ Resources to be copied for a particular platform. """
    resources = []
     
    """ List of platform specific dependencies """
    dependencies = []

    def __init__(self, package, name, **kwargs):
        self.package = package
        self.name = name
        self.resources = kwargs.get("resources", [])
        self.dependencies = kwargs.get("dependencies", [])
        self.imports = kwargs.get("imports", [])
        self.exports = kwargs.get("exports", [])
        self.generator_class = "onering.targets." + name + ".Generator"
        if "generator_class" in kwargs:
            self.generator_class = kwargs["generator_class"]
        elif "generator" in kwargs:
            genargs = kwargs["generator"]
            self.generator_class = genargs["class"]

    def get_generator_class(self):
        comps = self.generator_class.split(".")
        basemod = ".".join(comps[:-1])
        return importlib.import_module(basemod).Generator

class Package(object):
    """
    Describes what goes into a platform specific package (eg npm, jars, swift, pods etc), 
    that contains files generated from the schemas.
    """

    """ Name of the generated package. """
    name = "<package_name>"

    """ Version number of the package. """
    version = "0.0.1"

    """ Package description. """
    description = """Description of this package"""

    """ Which files are to be included in the generated package.  
    This could be individual files, wild cards, or directories.
    """
    inputs = [
        "schemas/common/*"
    ]

    """Set of platform specific configs.
    """
    platform_configs = {}

    """Dependent folders and jar paths where other onering schemas are to be loaded from.

    These are only for resolution of dependencies and will not candidates for code generation.
    """
    dependencies = {}

    resolvers = []

    """ Root folder of the output.  
    
    Files will be generated into:

        <output_root/platform_name/package_name>
    """
    output_root = None

    def __init__(self, package_spec_path = None):
        self.package_dir = None
        if package_spec_path:
            self.load_from_path(package_spec_path)

    def load_from_path(self, package_spec_path):
        package_spec_path = os.path.abspath(package_spec_path)
        if os.path.isdir(package_spec_path):
            package_spec_path = os.path.join(package_spec_path, "package.spec")
        
        assert os.path.isfile(package_spec_path), "%s is invalid" % package_spec_path
        pkgcode = compile(open(package_spec_path).read(), package_spec_path, "exec")
        pkgdata = {}
        exec pkgcode in pkgdata

        self.package_dir = os.path.abspath(os.path.dirname(package_spec_path))
        self.load(**pkgdata)

    def load(self, **kwargs):
        self.name = kwargs["name"]
        self.version = kwargs["version"]
        self.description = kwargs["description"]
        self.inputs = kwargs["inputs"]
        self.dependencies = kwargs.get("dependencies", {})
        self.resolvers = kwargs.get("resolvers", [])
        self.found_entities = {}
        self.platform_configs = {}
        self.current_platform = None
        self.template_dirs = [td if os.path.isabs(td) else os.path.join(self.package_dir, td)
                                for td in kwargs.get("template_dirs", [])]
        for key,value in kwargs.iteritems():
            if not key.startswith("platform_"): continue
            platform = key[len("platform_"):].strip()
            self.platform_configs[platform] = PlatformConfig(self, platform, **value)
            if not self.current_platform:
                self.current_platform = self.platform_configs[platform]

    def load_entities(self, context):
        """ Loads the package spec from a package.spec file. """

        context.pushdir()

        context.curdir = self.package_dir

        # First load entity resolver
        old_entity_resolver = context.entity_resolver
        context.entity_resolver = self._load_entity_resolver(context)

        # Load the necessary things common to all platforms
        # Each entry in the inputs list can be:
        # A file or a wildcard that is either an absolute path or
        # a path relative to the folder where the package_spec exists
        self.found_entities = LoaderActions(context).load_entries(self.inputs)

        # Now load dependencies so resolutions will succeed
        for dep_pkg_name,dep_pkg_path in self.dependencies.iteritems():
            abs_dep_pkg_path = os.path.abspath(os.path.join(self.package_dir, dep_pkg_path))
            context.ensure_package(dep_pkg_name, abs_dep_pkg_path)

        context.popdir()
        context.entity_resolver = old_entity_resolver
        return self

    def _load_entity_resolver(self, context):
        from onering.loaders import resolver as orresolver
        self.entity_resolver = orresolver.EntityResolver()
        for resolver in self.resolvers:
            entries_wc = resolver.get("entries")
            entry_dir = resolver.get("dir", resolver.get("jardir", None))
            edir = os.path.abspath(os.path.join(context.curdir, entry_dir))
            eprefix = resolver.get("prefix", None)
            for f in misc.collect_files(edir):
                if fnmatch.fnmatch(f, entries_wc):
                    if "jardir" in resolver:
                        self.entity_resolver.add_resolver(orresolver.ZipFilePathEntityResolver(f, eprefix))
                    else:
                        self.entity_resolver.add_resolver(orresolver.FilePathEntityResolver(f))
        return self.entity_resolver

    def select_platform(self, platname):
        self.current_platform = self.platform_configs[platname]

    def copy_resources(self, context, output_root):
        """Copy resources for a given platform to the output folder for thoe resources."""
        import shutil
        dirutils.ensure_dir(output_root)
        output_root = context.abspath(output_root)
        for source,dest_dir in self.current_platform.resources:
            source = os.path.join(self.package_dir, source)
            dest_dir = os.path.join(output_root, dest_dir)
            dirutils.ensure_dir(dest_dir)
            for f in glob.glob(source):
                shutil.copy(f, dest_dir)

    def get_generator(self, context, output_dir, platform_name = None):
        dirutils.ensure_dir(output_dir)
        self.template_loader = tplloader.TemplateLoader(self.template_dirs, parent_loader = context.template_loader)
        if platform_name is None:
            platform_name = self.current_platform.name
        platform = self.platform_configs[platform_name]
        generator_class = platform.get_generator_class()
        generator = generator_class(context, self, output_dir)
        return generator
