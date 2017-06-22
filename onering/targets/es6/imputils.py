
import os
import fnmatch
import ipdb
from typelib import annotations as tlannotations
from onering.utils.misc import FQN
from onering.utils.dirutils import open_file_for_writing
from onering.generator.backends import common as orgencommon
from onering.generator import core as orgencore
from onering.packaging.utils import is_type_entity, is_type_fun_entity, is_fun_entity, is_function_mapping_entity, is_api_functype

def base_filename_for_fqn(package, fqn):
    for fqn_wildcard, filename in package.current_platform.exports:
        if fnmatch.fnmatch(fqn, fqn_wildcard):
            return filename

class Importer(object):
    """ The purpose of this is give a method that takes a type reference/FQN and does two things:

        1. Ensures that the right "imports" for that FQN exists based on the language.
        2. After the imports are done, the final "signature" of the type is used.

        For example, if com.example.String was referenced, then (1) could be:

                var String = require("somelib").com.example.String;
            
            and (2) could be:

                x = new String(....)

        or alternatively:

            (1) ->  var somelib = require("somelib");
            (2) ->  x = new somelib.com.example.String(...)

        The key is that this is uniform for all uses of com.example.String within this
        compilation unit.  This also needs to ensure that two different FQNs with the same 
        base name also work (eg com.example.String and com.utils.String).

        This should be called once per compilation unit otherwise we could end up overriding
        imports.

        An interesting consideration is the role of entity path/loaders.  In languages like
        scala/java just referencing by FQN is enough and the class loader at runtime 
        (or build time) will look up the appropriate resource on disk (based on classpath items) 
        to resolve the import.  The resolution is not required manually.

        In langauges like python/JS/go it is slightly different for two reasons:
            1.  Even though a loader/resolver is required, since there is no implicit directory
                hierarchy of package/namespaces, an initial storage entity has to be pointed to.
               
                eg,

                JS:
                    
                    var root = require("somelib").a.b;
                    var String = root.<FQN>; // eg root.com.example.String

                    or use String explicitly as:

                        root.<FQN>

                Python:

                    from stringutils import models
                    from models import String

                    or rename it and use the alias everywhere

                    from models import String as MyString

                or in C/C++/ObjectiveC

                    import <std>
                    std::string x;

                    or

                    import <std>
                    using namespace::std
                    string x;

        Where is hard about the later is that we need a resolver at build time because if 
        a slack client depends on a schema in common models (or even its own models), then 
        the resolution for schema -> importable has to be somewhere.  We do not need to be 
        able to parse the actual importable, just know what it is so we can import it
        or generate import statements for it.  So back to the above examples, we may have:

            JS:

                FQN = a.b.c.D
                module = "x/y"
                importable = require("x/y")
                ensure_import("a.b.c.D") = importable.a.b.c.D

                so how can we resolve that a.b.c.D is in the module "x/y" or x/y....?

                This cannot be auto detected even with module specific conventions, 

                eg we know apizen.slack is in the apizen_slack package and convention
                is to have (apizen generated) models to be in <package>.models.

                For now hardcode this in the package.spec with wildcards or regex, eg:

                    apizen.common.* => require("apizen_common").models

                    this would resolve apizen.common.HttpRequest to

                    require("apizen_common").models.apizen.common.HttpReq..

                Package spec would have:

                    require_roots = {
                        "apizen.common.*": {
                            require: "apizen_common",
                            root: "models"
                        }
                    }

            Python:

                
                importable = 
                FQN = a.b

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
