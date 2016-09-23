
class SymbolTable(object):
    def __init__(self, parent = None):
        self._parent_table = parent
        self._curr_symtable = self
        self._children = []

    def get_var_for_binding(self, binding):
        """
        Given a variable or a field path, returns the register associated with that value.
        """
        pass

    def next_var_for_type(self, binding):
        """
        Given a type object, returns the next register/variable name for that type.
        """
        pass

    def register_var_with_type(self, varname, vartype):
        pass


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

