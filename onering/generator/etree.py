

class Node(object):
    """
    Describes a node in the expression tree.   Nodes are an abstract representation of 
    entries in a transformer.  By using abstract nodes, code generation can perform
    arbitrary node transformations to mean different things and have different rendering
    implementations.
    """
    def __init__(self, node_type, **properties):
        self._node_type = node_type
        self._parent = None
        self._properties = properties
        for name, value in properties.iteritems():
            if type(value) is Node:
                value._parent = self

    def __getattr__(self, name):
        if name in self._properties:
            return self._properties
        raise AttributeError

    def __setattr__(self, name, value):
        if name in self._properties:
            self._properties[name] = value
            if type(value) is Node:
                value._parent = self
        raise AttributeError

    @property
    def node_class(self):
        return self.__class__.__name__

    @property
    def node_type(self):
        return self._node_type

    @property
    def parent(self):
        return self._parent
