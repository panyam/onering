
import ipdb
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from typelib.annotations import Annotatable

class TransformerGroup(Annotatable):
    """
    A transformer group enables a set of transformers to be logically grouped.  This group and its
    data are available for all transformers within this group.   The group also determins how the
    """
    def __init__(self, fqn, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.fqn = fqn
        self._transformer_names = set()
        self._transformers = []

    def __repr__(self):
        return "<TG - ID: 0x%x, FQN: %s>" % (id(self), self.fqn)

    @property
    def all_transformers(self):
        return self._transformers[:]

    def add_transformer(self, transformer):
        if transformer.fqn in self._transformer_names:
            raise errors.OneringException("Duplicate transformer found: " % transformer.fqn)
        self._transformer_names.add(transformer.fqn)
        self._transformers.append(transformer)

    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.  This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        for transformer in self._transformers:
            transformer.resolve(context)

class Transformer(Annotatable):
    """
    Transformers define how an instance of one type can be transformed to an instance of another.
    """
    def __init__(self, fqn, src_fqn, dest_fqn, group = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.resolution = ResolutionStatus()
        self.fqn = fqn
        self.src_fqn = src_fqn
        self.dest_fqn = dest_fqn
        self.group = group
        self.temp_var_names = set()
        # explicit transformer rules
        self._implicit_statements = []
        self._explicit_statements = []

        # Keeps track of the counts of each type of auto-generated variable.
        self._vartable = {}

    def __repr__(self):
        return "<Transformer - ID: 0x%x, Name: %s (%s -> %s)>" % (id(self), self.fqn, self.src_fqn, self.dest_fqn)

    def is_temp_variable(self, varname):
        return varname in self.temp_var_names

    @property
    def all_statements(self):
        return self._implicit_statements + self._explicit_statements

    def add_statement(self, stmt):
        if not isinstance(stmt, Statement):
            raise errors.OneringException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        if stmt.is_temporary:
            varname = stmt.target_variable.value
            if self.is_temp_variable(varname):
                raise errors.OneringException("Duplicate temporary variable declared: '%s'" % varname)
            self.temp_var_names.add(varname)
        self._explicit_statements.append(stmt)

    def generate_ir(self, context):
        """
        Generates the IR for all the rules in this transformer.
        """
        if not self.resolution.succeeded:
            raise errors.OneringException("Resolution has not succeeded for transformer: %s" % self.fqn)

        symbol_table, instructions = generate_ir(self._implicit_statements + self._explicit_statements, context)


    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.  This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        def resolver_method():
            self._resolve(context)
        self.resolution.perform_once(resolver_method)


    def _resolve(self, context):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All expressions have their evaluated types set
        """
        type_registry = context.type_registry
        self.src_typeref = type_registry.get_typeref(self.src_fqn)
        self.dest_typeref = type_registry.get_typeref(self.dest_fqn)

        # First make sure we have implicit rules taken from the derivations if any
        self._implicit_statements = [] # self._evaluate_implicit_statements(context)

        # Now resolve all field paths appropriately
        for statement in self.all_statements:
            statement.resolve_types(self, context)

    def _evaluate_implicit_statements(self, context):
        """
        Given the source and dest types, evaluates all "get/set" rules that can be 
        inferred for shared types.   This is only possible if both src and dest types 
        share a common ancestor (or may be even at atmost 1 level).
        """

        # Step 1: Find common "ancestor" of each of the records
        ancestor = context.find_common_ancestor(self.src_typeref, self.dest_typeref)
        if ancestor is not None:
            # If the two types have no common ancestor then we cannot have auto rules
            pass

            # Variables are "locations" - a location is either a temp variable, or a (record + field_path)
            # Expressions are functions of locations:
            #   Function(multiple locations) results in locations being set
            #   Compound blocks are a collection of expressions that also get/set variables at a function scope
        return []


class Statement(object):
    def __init__(self, target_variable, expressions, is_temporary = False):
        self.expressions = expressions
        self.target_variable = target_variable
        self.is_temporary = is_temporary
        self.target_variable.from_source = False

    def resolve_types(self, transformer, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_types(transformer, context)

        # Resolve field paths that should come from dest type
        self.target_variable.resolve_types(transformer, context)

        if not self.is_temporary:
            # target variable type is set so verify that its type is same as the type of 
            # the "last" expression in the chain.
            pass
        else:
            # Then target variable is a temporary var declaration so set its type
            self.target_variable.evaluated_typeref = self.expressions[-1].evaluated_typeref

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
    def __init__(self, var_or_field_path, from_source = True):
        super(VariableExpression, self).__init__()
        self.from_source = from_source
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
        if self.is_field_path:
            from onering.core.resolvers import resolve_path_from_record
            starting_type = transformer.src_typeref if self.from_source else transformer.dest_typeref
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
        self.func_typeref = context.type_registry.get_typeref(self.func_fqn)

        if not self.func_typeref.is_resolved:
            ipdb.set_trace()

        # This is a variable so resolve it to either a local var or a parent + field_path
        for arg in self.func_args:
            arg.resolve_types(transformer, context)

        # Ensure that types match the types being sent to functions
        if len(self.func_args) != self.func_typeref.final_type.argcount:
            ipdb.set_trace()
            raise errors.OneringException("Function '%s' takes %d arguments, but encountered %d" % (self.function.constructor, self.function.arglimit, len(self.func_args)))

        for i in xrange(0, len(self.func_args)):
            arg = self.func_args[i]
            input_type = self.func_typeref.child_type_at(i)
            ipdb.set_trace()
            if arg.evaluated_typeref != input_type:
                raise errors.OneringException("Argument at index %d expected type (%s), found type (%s)" % (i, arg.evaluated_typeref, input_type))

        self._evaluated_typeref = self.function.output_type
