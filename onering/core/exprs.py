

import ipdb
from enum import Enum
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from typelib.annotations import Annotatable

class VarSource(Enum):
    AUTO            = -2
    LOCAL_VAR       = -1
    SOURCE_FIELD    = 0
    DEST_FIELD      = 1

class Statement(object):
    def __init__(self, target_variable, expressions, is_temporary = False):
        self.expressions = expressions
        self.target_variable = target_variable
        self.is_temporary = is_temporary
        self.target_variable.is_lhs = False
        if self.is_temporary:
            self.target_variable.source_type = VarSource.LOCAL_VAR
        else:
            self.target_variable.source_type = VarSource.AUTO

    def resolve_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # If type is not temporary then evaluate target var type first
        # This will help us with type inference going backwards
        if not self.is_temporary:
            self.target_variable.resolve_types(transformer, context)

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_types(transformer, context)

        last_expr = self.expressions[-1]
        if self.is_temporary:
            # Resolve field paths that should come from dest type
            # if self.is_temporary: ipdb.set_trace()
            self.target_variable.evaluated_typeref = last_expr.evaluated_typeref
            transformer.register_temp_var(str(self.target_variable.value), last_expr.evaluated_typeref)
        else:
            # target variable type is set so verify that its type is same as the type of 
            # the "last" expression in the chain.
            if type(last_expr) is FunctionCallExpression and not last_expr.function.output_known:
                last_expr.function.typeref.final_type.output_typeref = self.target_variable.evaluated_typeref
                last_expr.function.output_known = True

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
    def __init__(self, field_path, is_lhs, source_type = VarSource.SOURCE_FIELD):
        super(VariableExpression, self).__init__()
        self.is_lhs = True
        self.source_type = source_type
        self.value = field_path
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

    def set_evaluated_typeref(self, vartype):
        if self.source_type == VarSource.LOCAL_VAR:
            self._evaluated_typeref = vartype
        else:
            assert False, "cannot type evaluted type of a non local var"

    def check_types(self, context):
        if not self.is_field_path: return

    def resolve_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        from onering.core.resolvers import resolve_path_from_record

        # This is a variable so resolve it to either a local var or a parent + field_path
        if self.source_type == VarSource.AUTO:
            # Then see if it matches a local var or the src or dest var
            if self.is_lhs:
                res_result = resolve_path_from_record(transformer.src_typeref, self.value, context.type_registry, None)
                if res_result.is_valid:
                    self.source_type = VarSource.SRC_FIELD
                    print "Resource auto var: %s to source" % self.value
            else:
                res_result = resolve_path_from_record(transformer.dest_typeref, self.value, context.type_registry, None)
                if res_result.is_valid:
                    self.source_type = VarSource.DEST_FIELD
                    print "Resource auto var: %s to dest" % self.value

            if not res_result.is_valid:
                self.source_type = VarSource.LOCAL_VAR
                # get the value from the transformer's temp var table
                self._evaluated_typeref = transformer.temp_var_type(self.value)

        if self.source_type != VarSource.LOCAL_VAR:
            starting_type = transformer.src_typeref
            if self.source_type == VarSource.DEST_FIELD:
                starting_type = transformer.dest_typeref
            self.resolution_result = resolve_path_from_record(starting_type, self.value, context.type_registry, None)
            if not self.resolution_result.is_valid:
                raise errors.OneringException("Unable to resolve path '%s' in record '%s'" % (str(self.value), starting_type.fqn))
            self._evaluated_typeref = self.resolution_result.resolved_typeref
        else:
            # TODO - Any thing special for a local var?
            pass

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
        elif self._evaluated_typeref is None:
            self._evaluated_typeref = self.function.final_type.output_typeref
        return self._evaluated_typeref
