
from onering import readers

class SchemaLoader(object):
    """
    A class responsible for loading one or more schemas from either a file or from some in memory representation.
    """
    def __init__(self, thering):
        self.thering = thering
        self.readers = {
            "pegasus": readers.pegasus.read_from_path,
            "pdsc": readers.pegasus.read_from_path,
            "avsc": readers.avsc.read_from_path,
            "thrift": readers.thrift.read_from_path
        }

    def load(self, file_path, schema_type, root_dir = "."):
        """
        Given a path to a schema, one or more schemas are loaded from the file at this path
        """
        root_dir = os.path.abspath(root_dir)
        if not file_path.startswith("/"):
            file_path = os.path.abspath(os.path.join(root_dir, file_path))
        return self.readers[schema_type](self.thering, file_path)
