
import json, os
import ipdb
import zipfile

class EntityResolver(object):
    def __init__(self, *extensions):
        self.extensions = extensions or ["pdsc"]
        self.resolvers = []

    def add_resolver(self, resolver):
        if resolver not in self.resolvers:
            self.resolvers.append(resolver)

    def remove_resolver(self, resolver):
        for index,l in enumerate(self.resolvers):
            if resolver == l:
                del self.resolvers[index]
                return

    def resolve_schema(self, fqn, *schema_types):
        for resolver in self.resolvers:
            schema_contents = resolver.resolve_schema(fqn, *schema_types)
            if schema_contents: 
                print "Found Entity '%s' in Resolver: %s" % (fqn, resolver)
                return schema_contents

class FilePathEntityResolver(object):
    """
    Interface to return a file corresponding to a particular entry in a given (optional) namespace.
    """
    def __init__(self, path):
        self.path = path

    def __eq__(self, another):
        return type(another) == type(self) and self.path == another.path

    def __repr__(self):
        return "Dir<%s>" % self.path

    def __str__(self):
        return self.path

    def resolve_schema(self, fully_qualified_name, *schema_types):
        path = self.path
        full_path = path if path.endswith(os.sep) else path + os.sep
        full_path += fully_qualified_name.replace(".", os.sep)
        schema_types = schema_types or ["pdsc"]
        for schema_type in schema_types:
            final_path = full_path + "." + schema_type
            if os.path.isfile(final_path):
                return json.load(open(final_path))
        return None

class ZipFilePathEntityResolver(object):
    """
    Interface to return a file corresponding to a particular entry in a given (optional) namespace.
    """
    def __init__(self, jar_file, prefix = ""):
        self.prefix = prefix.strip()
        self.jar_file = jar_file

    def __repr__(self):
        return "Jar<%s:%s>" % (self.jar_file, self.prefix)

    def __eq__(self, another):
        return type(another) == type(self) and self.jar_file == another.jar_file

    def __str__(self):
        return self.jar_file

    def resolve_schema(self, fully_qualified_name, *schema_types):
        schema_types = schema_types or ["pdsc"]
        for schema_type in schema_types:
            full_path = fully_qualified_name.replace(".", os.sep) + "." + schema_type
            if self.prefix.endswith(os.sep):
                full_path = self.prefix + full_path
            elif self.prefix:
                full_path = self.prefix + os.sep + full_path

            jar_file = self.jar_file
            zf = zipfile.ZipFile(jar_file, "r")
            if len(filter(lambda x: x == full_path, zf.namelist())) > 0:
                return json.loads(zf.read(full_path))
        return None
