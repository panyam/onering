

import ipdb
from enum import Enum
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from typelib.annotations import Annotatable

class VarSource(Enum):
    LOCAL_VAR       = -1
    SOURCE_FIELD    = 0
    DEST_FIELD      = 1

class Statement(object):
    def __init__(self, target_variable, expressions, is_temporary = False):
        self.expressions = expressions
        self.target_variable = target_variable
        self.is_temporary = is_temporary
        if self.is_temporary:
            self.target_variable.source_type = VarSource.LOCAL_VAR
        else:
            self.target_variable.source_type = VarSource.DEST_FIELD

    def resolve_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_types(transformer, context)

        # Resolve field paths that should come from dest type
        # if self.is_temporary: ipdb.set_trace()
        self.target_variable.resolve_types(transformer, context)

        if not self.is_temporary:
            # target variable type is set so verify that its type is same as the type of 
            # the "last" expression in the chain.
            pass
        else:
            # Then target variable is a temporary var declaration so set its type
            # Here the last expression CANNOT require output type inferrence because then
            # the type of this variable cannot be inferred
            last_expr = self.expressions[-1]
            self.target_variable.evaluated_typeref = last_expr.evaluated_typeref

class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in transformers
    (or in derivations during type streaming but type streaming is "kind of" a transformer anyway.
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

    def resolve_types(self, transformer, context):
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
        if t in (string, unicode):
            self._evaluated_typeref = context.type_registry.get_typeref("string")
        elif t is int:
            self._evaluated_typeref = context.type_registry.get_typeref("int")
        elif t is bool:
            self._evaluated_typeref = context.type_registry.get_typeref("bool")
        elif t is float:
            self._evaluated_typeref = context.type_registry.get_typeref("float")

    def __repr__(self):
        return "<Literal - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

class VariableExpression(Expression):
    def __init__(self, var_or_field_path, source_type = VarSource.SOURCE_FIELD):
        super(VariableExpression, self).__init__()
        self.source_type = source_type
        self.value = var_or_field_path

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

    def set_evaluated_typeref(self, vartype):
        if not self.is_field_path:
            self._evaluated_typeref = vartype

    def check_types(self, context):
        if not self.is_field_path: return

    @property
    def is_field_path(self):
        return type(self.value) is FieldPath

    def resolve_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # This is a variable so resolve it to either a local var or a parent + field_path
        if self.source_type != VarSource.LOCAL_VAR:
            from onering.core.resolvers import resolve_path_from_record
            starting_type = transformer.src_typeref
            if self.source_type == VarSource.DEST_FIELD:
                starting_type = transformer.dest_typeref
            result = resolve_path_from_record(starting_type, self.value, context.type_registry, None)
            if not result.is_valid:
                raise errors.OneringException("Unable to resolve path '%s' in record '%s'" % (str(self.value), starting_type.fqn))
            self._evaluated_typeref = result.resolved_typeref
        else:
            ipdb.set_trace()

class ListExpression(Expression):
    def __init__(self, values):
        super(ListExpression, self).__init__()
        self.values = values

class DictExpression(Expression):
    def __init__(self, values):
        super(DictExpression, self).__init__()
        self.values = values

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
    def __init__(self, func_fqn, func_args = None):
        super(FunctionCallExpression, self).__init__()
        self.func_fqn = func_fqn
        self.func_args = func_args

    def resolve_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        function = self.function = context.get_function(self.func_fqn)
        func_typeref = self.function.typeref
        func_type = function.final_type

        # This is a variable so resolve it to either a local var or a parent + field_path
        for arg in self.func_args:
            arg.resolve_types(transformer, context)

            if function.inputs_need_inference and not function.inputs_known:
                func_typeref.final_type.add_arg(arg.evaluated_typeref)

        # Mark inputs as having been inferred
        function.inputs_known = True

        if not function.inputs_need_inference:
            if len(self.func_args) != func_typeref.final_type.argcount:
                ipdb.set_trace()
                raise errors.OneringException("Function '%s' takes %d arguments, but encountered %d" %
                                                (function.constructor, function.arglimit, len(self.func_args)))

            for i in xrange(0, len(self.func_args)):
                arg = self.func_args[i]
                input_typeref = func_typeref.final_type.arg_at(i).typeref
                if arg.evaluated_typeref != input_typeref:
                    raise errors.OneringException("Argument at index %d expected type (%s), found type (%s)" % (i, arg.evaluated_typeref, input_typeref))

        if function.output_known:
            self._evaluated_typeref = func_type.output_typeref

    @property
    def evaluated_typeref(self):
        if not self.function.output_known:
            output_typeref = self.function.final_type.output_typeref
            if not output_typeref or output_typeref.is_unresolved:
                raise errors.OneringException("Output type of function '%s' not known as type inference is requested" % self.func_fqn)
        return self._evaluated_typeref
