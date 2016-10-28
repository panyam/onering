
import ipdb
import itertools

class SymbolTable(object):
    def __init__(self, parent = None, counter = None):
        self.counter = counter or itertools.count()
        self._parent_table = parent
        self._curr_symtable = self
        self._children = []
        self._types_for_names = {}
        self._var_for_path = {}

    @property
    def declarations(self):
        return [ (varname, self._types_for_names[varname]) for varname in self._children ]

    def get_var_for_path(self, path, typeref):
        """
        Given a variable or a field path, returns the register associated with that value.
        """
        if path not in self._var_for_path:
            self._var_for_path[path] = self.next_var(typeref)
        return self._var_for_path[path]

    def next_var(self, typeref):
        """
        Given a type object, returns the next register/variable name for that type.
        """
        varname = "var_%d" % self.counter.next()
        while varname in self._types_for_names:
            varname = "var_%d" % self.counter.next()
        return self.register_var(varname, typeref)

    def register_var(self, varname, typeref):
        assert type(varname) in (str, unicode)
        if varname in self._types_for_names:
            assert False, "Variable with name '%s' varname already exists" % varname
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

