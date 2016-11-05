

class Node(object):
    """
    Describes a node in the expression tree.   Nodes are an abstract representation of 
    entries in a transformer.  By using abstract nodes, code generation can perform
    arbitrary node transformations to mean different things and have different rendering
    implementations.
    """
    def __init__(self, node_type, parent = None,children = None, properties = None):
        self.parent = parent
        self.children = children or []
        self.properties = properties

