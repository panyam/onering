
import os
import fnmatch
import ipdb
from onering.packaging.utils import is_type_entity, is_typefun_entity, is_fun_entity, is_function_mapping_entity

def base_filename_for_fqn(package, fqn):
    for fqn_wildcard, filename in package.current_platform.exports:
        if fnmatch.fnmatch(fqn, fqn_wildcard):
            return filename

class Importer(object):
    """ The purpose of this is give a method that takes a type reference/FQN and does two things:

        1. Ensures that the right "imports" for that FQN exists based on the language.
        2. After the imports are done, the final "signature" of the type is used.
    """
    def __init__(self, platform_config):
        self.platform_config = platform_config

        # This tells which "requires" have been imported as which variables
        self._generated_imports = {}
        # This is the reverse lookup of above, ie varname -> require statements
        self._imported_varnames = {}
        
        # Cached mappings of FQNs and how they are to be rendered
        # after fixing resolutions and imports etc
        self._fqn_mappings = {}

    def render_imports(self):
        return "\n".join("var %s = %s;" % (varname, import_statement) 
                                for import_statement, varname in 
                                    self._generated_imports.iteritems())
            
    def ensure(self, fqn):
        if fqn not in self._fqn_mappings:
            # First check if this model is part of the current package
            # being generated in which case we shouldnt be looking at 
            # imports
            for fqn_wildcard, resolver in self.platform_config.imports:
                if fnmatch.fnmatch(fqn, fqn_wildcard):
                    source_package = resolver["package"]
                    obj_root = resolver.get("root", None)
                    self._fqn_mappings[fqn] = self._ensure_imported(source_package, obj_root, fqn)
                    break
        return self._fqn_mappings[fqn]

    def _ensure_imported(self, source_package, obj_root, fqn):
        # see if source_package + obj_root has already been required as a variable, 
        # if so return it otherwise create a new import with a new var
        if obj_root:
            import_stmt = "require('%s').%s" % (source_package, obj_root)
        else:
            import_stmt = "require('%s')" % source_package
        if import_stmt not in self._generated_imports:
            # how to find the varname?
            # TODO - generate better names!
            if obj_root:
                basename = varname = obj_root.split(".")[-1]
            else:
                basename = varname = source_package.split("/")[-1]
            index = 0
            while varname in self._imported_varnames:
                varname = basename + str(index)
                index += 1
            self._generated_imports[import_stmt] = varname
            self._imported_varnames[varname] = import_stmt
        varname = self._generated_imports[import_stmt]
        return "%s.%s" % (varname, fqn)
