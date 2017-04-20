
import ipdb
from itertools import izip
from typelib.core import Entity
from typelib import unifier as tlunifier
from onering.utils.misc import ResolutionStatus
from onering.core import exprs as orexprs
from onering.errors import OneringException

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
        self.is_external = False

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
        return [(x.name, x.typeref) for x in self.typeref.args]

    @property
    def src_typerefs(self):
        return [x.typeref for x in self.typeref.args]

    @property
    def dest_typeref(self):
        return self.typeref.output_typeref

    @property
    def dest_fqn(self):
        if self.typeref.output_typeref:
            return self.typeref.output_typeref.fqn
        else:
            return "None"

    def add_statement(self, stmt):
        if not isinstance(stmt, orexprs.Statement):
            raise OneringException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        # Check types and variables in the statements
        self._explicit_statements.append(stmt)

    @property
    def all_statements(self):
        return self._explicit_statements

    def local_variables(self, yield_src = True, yield_dest = True, yield_locals = True):
        if yield_src:
            for src_varname, src_typeref in self.source_variables:
                yield src_varname, src_typeref, False
        if yield_dest:
            yield self.dest_varname, self.dest_typeref, False
        if yield_locals:
            for vname, vtype in self.temp_variables.iteritems():
                yield vname, vtype, True

    def matches_input(self, context, input_typerefs):
        """Tells if the input types can be accepted as argument for this transformer."""
        if type(input_typerefs) is not list:
            input_types = [input_typerefs]
        if len(input_typerefs) != len(self.src_fqns):
            return False
        source_types = [x.final_entity for x in self.src_typerefs]
        input_types = [x.final_entity for x in input_typerefs]
        return all(tlunifier.can_substitute(st, it) for (st,it) in izip(source_types, input_types))

    def matches_output(self, context, output_type):
        dest_type = self.dest_typeref.final_entity
        return tlunifier.can_substitute(output_type, dest_type)

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype):
        assert type(varname) in (str, unicode)
        if varname in (x.name for x in self.typeref.args):
            raise OneringException("Duplicate temporary variable '%s'.  Same as source." % varname)
        elif varname == self.dest_varname:
            raise OneringException("Duplicate temporary variable '%s'.  Same as target." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise OneringException("Duplicate temporary variable declared: '%s'" % varname)
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
        src_typerefs = [arg.typeref for arg in self.typeref.args]
        dest_typeref = self.typeref.output_typeref
        for typeref in src_typerefs + [dest_typeref]:
            # Yep find it up *its* module chain!
            self.resolve_binding(typeref)

        # Now resolve all field paths appropriately
        for index,statement in enumerate(self.all_statements):
            statement.resolve_bindings_and_types(self, context)
