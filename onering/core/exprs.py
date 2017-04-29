

import ipdb
from enum import Enum
from onering import errors
from onering.utils.misc import ResolutionStatus
from onering.core.utils import FieldPath
from typelib import core as tlcore
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier

class Statement(object):
    def __init__(self, expressions, target_variable, is_temporary = False):
        self.expressions = expressions
        self.target_variable = target_variable
        self.target_variable.is_temporary = is_temporary or target_variable.field_path.get(0) == '_'
        self.is_implicit = False
        if self.target_variable.is_temporary:
            assert target_variable.field_path.length == 1, "A temporary variable cannot have nested field paths"

    @property
    def is_temporary(self):
        return self.target_variable.is_temporary

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        if not self.is_temporary:
            self.target_variable.resolve_bindings_and_types(function, context)

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_bindings_and_types(function, context)

        last_expr = self.expressions[-1]
        if self.target_variable.is_temporary:
            # Resolve field paths that should come from dest type
            self.target_variable.evaluated_typeref = last_expr.evaluated_typeref
            function.register_temp_var(str(self.target_variable.field_path), last_expr.evaluated_typeref)

class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in functions
    (or in derivations during type streaming but type streaming is "kind of" a function anyway.
    """
    def __init__(self):
        self._evaluated_typeref = None

    @property
    def evaluated_typeref(self):
        if not self._evaluated_typeref:
            raise errors.OneringException("Type checking failed for '%s'" % repr(self))
        return self._evaluated_typeref

    @evaluated_typeref.setter
    def evaluated_typeref(self, vartype):
        self.set_evaluated_typeref(vartype)

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        pass


class LiteralExpression(Expression):
    """
    An expression that contains a literal value like a number, string, boolean, array, or map.
    """
    def __init__(self, value):
        super(LiteralExpression, self).__init__()
        self.value = value

    def check_types(self, context):
        t = type(self.value)
        if t in (str, unicode):
            self._evaluated_typeref = context.global_module.get("string")
        elif t is int:
            self._evaluated_typeref = context.global_module.get("int")
        elif t is bool:
            self._evaluated_typeref = context.global_module.get("bool")
        elif t is float:
            self._evaluated_typeref = context.global_module.get("float")

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        self.check_types(context)

    def __repr__(self):
        return "<Literal - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

class DictExpression(Expression):
    def __init__(self, values):
        super(DictExpression, self).__init__()
        self.values = values

class ListExpression(Expression):
    def __init__(self, values):
        super(ListExpression, self).__init__()
        self.values = values

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        for expr in self.values:
            expr.resolve_bindings_and_types(function, context)

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        any_typeref = tlcore.SymbolRef("any")
        function.resolve_binding(any_typeref)
        self._evaluated_typeref = tlcore.EntityRef(tlcore.ArrayType(None, function, any_typeref), None, function)

class TupleExpression(Expression):
    def __init__(self, values):
        super(TupleExpression, self).__init__()
        self.values = values or []

class FunctionCallExpression(Expression):
    """
    An expression for denoting a function call.  Function calls can only be at the start of a expression stream, eg;

    f(x,y,z) => H => I => J

    but the following is invalid:

    H => f(x,y,z) -> J

    because f(x,y,z) must return an observable and observable returns are not supported (yet).
    """
    def __init__(self, func_ref, func_args = None):
        super(FunctionCallExpression, self).__init__()
        assert issubclass(func_ref.__class__, tlcore.EntityRef)
        self.func_ref = func_ref
        self.func_args = func_args

    def resolve_bindings_and_types(self, parent_function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        try:
            parent_function.resolve_binding(self.func_ref)
        except:
            raise errors.OneringException("Function '%s' not found" % self.func_fqn)

        func_type = self.func_ref.final_entity
        if not func_type:
            ipdb.set_trace()

        # Each of the function arguments is either a variable or a value.  
        # If it is a variable expression then it needs to be resolved starting from the
        # parent function that holds this statement (along with any other locals and upvals)
        for arg in self.func_args:
            arg.resolve_bindings_and_types(parent_function, context)

        if len(self.func_args) != func_type.argcount:
            ipdb.set_trace()
            raise errors.OneringException("Function '%s' takes %d arguments, but encountered %d" %
                                            (function.fqn, func_type.argcount, len(self.func_args)))

        for i in xrange(0, len(self.func_args)):
            arg = self.func_args[i]
            peg_typeref = arg.evaluated_typeref
            hole_typeref = func_type.arg_at(i).typeref
            if not tlunifier.can_substitute(peg_typeref.final_entity, hole_typeref.final_entity):
                ipdb.set_trace()
                raise errors.OneringException("Argument at index %d expected (hole) type (%s), found (peg) type (%s)" % (i, hole_typeref, peg_typeref))

        self._evaluated_typeref = func_type.output_typeref

    @property
    def evaluated_typeref(self):
        """
        if not self.function.output_known:
            output_typeref = self.function.final_type.output_typeref
            if not output_typeref or output_typeref.is_unresolved:
                raise errors.OneringException("Output type of function '%s' not known as type inference is requested" % self.func_fqn)
        """
        if self._evaluated_typeref is None:
            self._evaluated_typeref = self.func_ref.final_entity.output_typeref
        return self._evaluated_typeref

class VariableExpression(Expression):
    def __init__(self, field_path):
        super(VariableExpression, self).__init__()
        self.is_temporary = False
        self.field_path = field_path
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def set_evaluated_typeref(self, vartype):
        if self.is_temporary:
            self._evaluated_typeref = vartype
        else:
            assert False, "cannot get evaluted type of a non local var: %s" % self.field_path

    def check_types(self, context):
        if not self.is_field_path: return

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        assert self._evaluated_typeref == None, "Type has already been resolved, should not have been called twice."
        from onering.core.resolvers import resolve_path_from_record

        first, field_path_tail = self.field_path.pop()
        self.is_temporary = self.is_temporary or first == "_" or function.is_temp_variable(first)
        if self.is_temporary: # We have a local var declaration
            # So add to function's temp var list if not a duplicate
            if first == "_":
                self._evaluated_typeref = function.resolve_binding(tlcore.SymbolRef("void"))
            else:
                # get type from function
                self._evaluated_typeref = function.temp_var_type(self.field_path)
        else:
            # See which of the params we should bind to
            self.field_resolution_result = None

            for src_varname, src_typeref in function.source_variables:
                if src_varname == first:
                    if field_path_tail.length > 0:
                        self.field_resolution_result = resolve_path_from_record(src_typeref, field_path_tail, context, None)
                    else:
                        self._evaluated_typeref = src_typeref
                    break
            else:
                if function.dest_typeref and function.dest_varname == first:
                    # If we are dealing with an output variable, we dont want to directly reference the var
                    # because the output value could be created (via a constructor) at the end.  Instead
                    # save to other newly created temp vars and finally collect them and do bulk setters 
                    # on the output var or a constructor on the output var or both.
                    self.field_resolution_result = resolve_path_from_record(function.dest_typeref, field_path_tail, context, None)

            if not self._evaluated_typeref:
                if not self.field_resolution_result or not self.field_resolution_result.is_valid:
                    ipdb.set_trace()
                    raise errors.OneringException("Invalid field path '%s'" % self.field_path)
                self._evaluated_typeref = self.field_resolution_result.resolved_typeref
