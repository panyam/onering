

import ipdb
from enum import Enum
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier

class VarSource(Enum):
    AUTO        = -2
    LOCAL       = 0
    SOURCE      = -1
    DEST        = 1

class Statement(object):
    def __init__(self, transformer, expressions, target_variable, is_temporary = False):
        self.transformer = transformer
        self.expressions = expressions
        self.target_variable = target_variable
        self.is_temporary = is_temporary
        self.target_variable.readonly = False
        self.target_variable.source_type = VarSource.AUTO
        self.is_implicit = False
        if self.is_temporary:
            assert target_variable.value.length == 1, "A temporary variable cannot have nested field paths"
            self.target_variable.source_type = VarSource.LOCAL

    def resolve_bindings_and_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        self.target_variable.resolve_bindings_and_types(transformer, context)

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_bindings_and_types(transformer, context)

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

    def resolve_bindings_and_types(self, transformer, context):
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
            self._evaluated_typeref = context.type_registry.get_typeref("string")
        elif t is int:
            self._evaluated_typeref = context.type_registry.get_typeref("int")
        elif t is bool:
            self._evaluated_typeref = context.type_registry.get_typeref("bool")
        elif t is float:
            self._evaluated_typeref = context.type_registry.get_typeref("float")

    def resolve_bindings_and_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        self.check_types(context)

    def __repr__(self):
        return "<Literal - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

class VariableExpression(Expression):
    def __init__(self, field_path, readonly, source_type = VarSource.SOURCE):
        super(VariableExpression, self).__init__()
        self.readonly = True
        self.source_type = source_type
        self.value = field_path
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

    def set_evaluated_typeref(self, vartype):
        if self.source_type == VarSource.LOCAL:
            self._evaluated_typeref = vartype
        else:
            assert False, "cannot get evaluted type of a non local var: %s" % self.value

    def check_types(self, context):
        if not self.is_field_path: return

    def resolve_bindings_and_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        assert self._evaluated_typeref == None, "Type has already been resolved, should not have been called twice."
        from onering.core.resolvers import resolve_path_from_record

        if self.source_type == VarSource.LOCAL: # We have a local var declaration
            # So add to transformer's temp var list if not a duplicate
            transformer.register_temp_var(str(self.value), None)
            self.normalized_field_path = self.value.copy()

        if self.source_type == VarSource.AUTO:
            # Find which variable to bind to:
            # If it is readonly then also look at src/* first
            # Now we should also look to dest/* locals/*
            # If all fail, then do the same but 
            first, tail_field_path = self.value.pop()

            starting_type = None
            for varname,vartype,varclass in transformer.local_variables(yield_src = self.readonly):
                if varname == first:
                    starting_type = vartype
                    starting_varname = varname
                    starting_source = varclass
                    break

            field_resolution_result = None
            if starting_type:
                # Then resolve the rest of the field path from here
                # Then find the whole field path from one of the either source, dest or "current" local var only
                # Depending on whether the var is writeable or not
                if tail_field_path.length > 0:
                    field_resolution_result = resolve_path_from_record(starting_type, tail_field_path, context.type_registry, None)
                    if not field_resolution_result.is_valid:
                        ipdb.set_trace()
                        raise errors.OneringException("Invalid field path '%s' from '%s'" % (self.value, starting_varname))
                    else:
                        self.source_type = starting_source
                        self.normalized_field_path = self.value.copy()
                        self._evaluated_typeref = field_resolution_result.resolved_typeref
                else:
                    self.source_type = starting_source
                    self.normalized_field_path = self.value.copy()
                    self._evaluated_typeref = starting_type
            else:
                # Could not resolve it explicitly, try doing so implicitly from source and dest (if readonly) or just dest.
                # Note - no need to test for local as that would have been tested previous case when we tested
                # for src, dest and locals
                if self.readonly:
                    self.source_type = VarSource.SOURCE
                    last_resolved = None
                    field_resolution_result = None
                    resolved_src_name = None
                    for src_varname, src_typeref in transformer.source_variables:
                        field_resolution_result = resolve_path_from_record(src_typeref, self.value, context.type_registry, None)
                        if field_resolution_result.is_valid:
                            if not last_resolved:
                                last_resolved = field_resolution_result
                                resolved_src_name = src_varname
                            else:
                                raise errors.OneringException("More than one source resolves: '%s'" % self.value)

                # We should have exactly one source that resolves otherwise we have an error
                if field_resolution_result is None or not field_resolution_result.is_valid:
                    self.source_type = VarSource.DEST
                    field_resolution_result = resolve_path_from_record(transformer.dest_typeref, self.value, context.type_registry, None)

                if not field_resolution_result.is_valid:
                    self.source_type = VarSource.AUTO
                    raise errors.OneringException("Invalid field path '%s'" % self.value)
                else:
                    self._evaluated_typeref = field_resolution_result.resolved_typeref
                    if self.source_type == VarSource.SOURCE:
                        self.normalized_field_path = self.value.push(resolved_src_name)
                    elif self.source_type == VarSource.DEST:
                        self.normalized_field_path = self.value.push(transformer.dest_varname)

            self.field_resolution_result = field_resolution_result
            return

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

    def resolve_bindings_and_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        function = self.function = context.get_function(self.func_fqn)
        func_typeref = self.function.typeref
        func_type = function.final_type

        # This is a variable so resolve it to either a local var or a parent + field_path
        for arg in self.func_args:
            arg.resolve_bindings_and_types(transformer, context)
            if function.inputs_need_inference and not function.inputs_known:
                func_typeref.final_type.add_arg(arg.evaluated_typeref)

        # Mark inputs as having been inferred
        function.inputs_known = True

        if not function.inputs_need_inference:
            if len(self.func_args) != func_typeref.final_type.argcount:
                ipdb.set_trace()
                raise errors.OneringException("Function '%s' takes %d arguments, but encountered %d" %
                                                (function.fqn, func_type.argcount, len(self.func_args)))

            for i in xrange(0, len(self.func_args)):
                arg = self.func_args[i]
                input_typeref = func_typeref.final_type.arg_at(i).typeref
                if not tlunifier.can_substitute(input_typeref.final_type, arg.evaluated_typeref.final_type):
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
