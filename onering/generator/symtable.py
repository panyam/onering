
import ipdb
import itertools

class SymbolTable(object):
    def __init__(self, parent = None, counter = None):
        self.counter = counter or itertools.count()
        self._parent_table = parent
        self._curr_symtable = self
        self._children = []
        self._types_for_names = {}

    def get_var(self, var_or_field_path):
        """
        Given a variable or a field path, returns the register associated with that value.
        """
        ipdb.set_trace()

    def next_var(self, typeref):
        """
        Given a type object, returns the next register/variable name for that type.
        """
        varname = "var_%d" % self.counter.next()
        return self.register_var(varname, typeref)

    def register_var(self, varname, typeref):
        if varname in self._types_for_names:
            assert False, "Variable with name '%s' varname already exists"
        self._types_for_names[varname] = typeref
        self._children.append(varname)
        return varname


    def push(self):
        """
        Pushes a new scope onto the table.
        """
        newsymtable = SymbolTable(self)
        self._push_count += 1
        self._children.append(newsymtable)
        self._curr_symtable = newsymtable

    def pop(self):
        if self._push_count > 0 and self._curr_symtable._parent_table:
            self._push_count -= 1
            self._curr_symtable = self._curr_symtable._parent_table

