
class Document(object):
    """
    A Onering document that contains a bunch of imports followed by one or more type definitions.
    """
    def __init__(self):
        self.namespace = None
        self.imports = []
        self.declarations = {}

class TypeDeclaration(object):
    """
    A Onering type declaration.   Types could be records, enums, unions or others defined
    in the datatypes.
    """
    def __init__(self, name, docstring = "", annotations = []):
        self.name = name
        self.docstring = docstring
        self.annotations = annotations
