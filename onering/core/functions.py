
import ipdb
from typelib.core import Entity
from onering.utils.misc import ResolutionStatus
from onering.core import exprs as orexprs

class Function(Entity):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, container, typeref, annotations = None, docs = ""):
        Entity.__init__(self, name, container, annotations, docs)
        self.typeref = typeref
        self.statements = []
        self.resolution = ResolutionStatus()
        self.dest_varname = "dest"

        self.temp_variables = {}
        # explicit transformer rules
        self._explicit_statements = []

        # Keeps track of the counts of each type of auto-generated variable.
        self._vartable = {}

    def __repr__(self):
        return "<Function(0x%x) %s (%s -> %s)>" % (id(self), self.fqn, ",".join(self.src_fqns), self.dest_fqn)

    @property
    def src_fqns(self):
        return [x.typeref.fqn for x in self.typeref.args]

    @property
    def source_variables(self):
        return [(x.name, x.typeref.fqn) for x in self.typeref.args]

    @property
    def dest_fqn(self):
        return self.typeref.output_typeref.fqn

    def add_statement(self, stmt):
        if not isinstance(stmt, orexprs.Statement):
            raise errors.OneringException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        # Check types and variables in the statements
        self._explicit_statements.append(stmt)

    @property
    def all_statements(self):
        return self._explicit_statements

    def local_variables(self, yield_src = True, yield_dest = True, yield_locals = True):
        if yield_src:
            for src_varname, src_typeref in self.source_variables:
                yield src_varname, src_typeref, orexprs.VarSource.SOURCE
        if yield_dest:
            yield self.dest_varname, self.dest_typeref, orexprs.VarSource.DEST
        if yield_locals:
            for vname, vtype in self.temp_variables.iteritems():
                yield vname, vtype, orexprs.VarSource.LOCAL

    def matches_input(self, context, input_types):
        """Tells if the input types can be accepted as argument for this transformer."""
        if type(input_types) is not list:
            input_types = [input_types]
        if len(input_types) != len(self.src_fqns):
            return False
        source_types = map(context.type_registry.get_final_type, self.src_fqns)
        return all(tlunifier.can_substitute(st, it) for (st,it) in izip(source_types, input_types))

    def matches_output(self, context, output_type):
        dest_type = context.type_registry.get_final_type(self.dest_fqn)
        return tlunifier.can_substitute(output_type, dest_type)

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype):
        assert type(varname) in (str, unicode)
        if varname in self.src_varnames:
            raise errors.OneringException("Duplicate temporary variable '%s'.  Same as source." % varname)
        elif varname == self.dest_varname:
            raise errors.OneringException("Duplicate temporary variable '%s'.  Same as target." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise errors.OneringException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

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
        # Resolve types here - bind them to somewhere along the module chain where they are visible!
        self.src_typerefs = [arg.typeref for arg in self.typeref.args]
        self.dest_typeref = self.typeref.output_typeref
        for typeref in self.src_typerefs + [self.dest_typeref]:
            if not typeref.is_resolved:
                # Yep find it up *its* module chain!
                ipdb.set_trace()
            assert typeref.final_entity

        # Now resolve all field paths appropriately
        for index,statement in enumerate(self.all_statements):
            statement.resolve_bindings_and_types(self, context)
