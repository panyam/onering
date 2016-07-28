
import utils

class FieldGraph(object):
    """
    Answers questions around which fields in a particular model affect fields in another model.
    """
    class Edge(object):
        def __init__(self, field, label):
            assert type(label) in (str, unicode), "Label must be a string"
            self.field = field
            self.label = label 

        def __hash__(self):
            return hash(self.field.fqn + "/" + self.label)

        def __cmp__(self, other):
            result = cmp(self.field, other.field)
            if result == 0:
                result = cmp(self.label, other.label)
            return result

    def __init__(self):
        self.edges = {}

    def has_field_edge(self, source_field, dep_type = None):
        return len(self.get_field_edges(source_field, dep_type)) > 0

    def get_field_edges(self, source_field, dep_type = None):
        """
        Given source field returns the set of fields depend on this field along with the dependency types.
        """
        edges = []
        if source_field in self.edges:
            edges = self.edges[source_field]
            if dep_type:
                edges = filter(lambda x: x.label == dep_type, edges)
        return edges

    def add_field_edge(self, source_field, target_field, dep_type):
        """
        Adds a field as a dependancy of a given field along with the type of dependancy (mandatory).
        """
        if source_field not in self.edges:
            self.edges[source_field] = set()
        self.edges[source_field].add(FieldGraph.Edge(target_field, dep_type))

    def remove_field_edge(self, source_field, target_field, dep_type = None):
        """
        Given the name of a field in the source type, returns the set of fields
        in the target type that depend on this field (either during name mapping or
        during instance transformations).
        """
        if source_field in self.edges:
            if dep_type:
                self.edges[source_field].remove(FieldGraph.Edge(target_field, dep_type))
            else:
                del self.edges[source_field]

    def clear(self):
        """
        Clears the graph.
        """
        self.edges = {}


    def print_graph(self, fields = None):
        print "Field Graph: "
        # import ipdb ; ipdb.set_trace()
        for key in sorted(self.edges.keys()):
            if fields and key not in fields:
                print "Field not found: '%s'" % key
            else:
                value = self.edges[key]
                # print "KeyType, Key: ", type(key), key
                print "%s (Type: %s)" % (key, key.field_type.signature)
                for edge in value:
                    print "    -> %s (Type: %s) via %s" % (edge.field.fqn, edge.field.field_type.signature, edge.label)

