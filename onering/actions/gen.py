
import os, sys
import ipdb
from onering import dsl
from onering import resolver
from onering import utils as orutils
from onering.actions.base import ActionGroup

class GeneratorActions(ActionGroup):
    """
    Actions to generate language/platform specific models, transformers etc from
    schema files.
    """
    def __init__(self, context):
        ActionGroup.__init__(context)

    def codegen(self, schemas_or_fqns, platform = None, template = None):
        """
        Generate code for the given type schemas.

        **Parameters:**
            schemas_or_fqns -   A list of schema (typerefs) or FQNs whose code is to be generated.
            platform        -   If a platform is specified then the generated output is for the 
                                particular platform.  If the platform is not specified then the platform 
                                specified in the type's "onering.backend" annotation is used.
                                If this annotation is not specified then the default platform is used. 
                                Otherwise an error is thrown.
            template        -   Like the platform, specifies the template to use.  The order of resolution
                                of templates to use is first by the specified one, followed by the 
                                one specified in its annotation, followed by a default template (if any), 
                                otherwise an error is thrown.
        """
        for entry in schemas_or_fqns:
            source_typeref = entry
            if type(source_typeref) in (str, unicode):
                source_typeref = self.context.type_registry.get_typeref(source_typeref)
            orgenutils.generate_schemas(source_typeref, self.context, platform, template)

    def codegen_transformers(self, tgroups_or_fqns, platform = None, template = None):
        """
        Generate code for the given transformer groups.

        **Parameters:**
            tgroups_or_fqns -   A list of transformer groups (typerefs) or FQNs whose code is to be generated.
            platform        -   If a platform is specified then the generated output is for the 
                                particular platform.  If the platform is not specified then the platform 
                                specified in the type's "onering.backend" annotation is used.
                                If this annotation is not specified then the default platform is used. 
                                Otherwise an error is thrown.
            template        -   Like the platform, specifies the template to use.  The order of resolution
                                of templates to use is first by the specified one, followed by the 
                                one specified in its annotation, followed by a default template (if any), 
                                otherwise an error is thrown.
        """
        # Awwwwright resolutions succeeded so now generate them!
        # Awwwwright resolutions succeeded so now generate them!
        for entry in tgroups_or_fqns:
            tg = entry
            if type(tg) in (str, unicode):
                tg = self.context.get_transformer_group(tg)
            orgenutils.generate_transformers(tg, self.context, platform, template)

    def codegen_interfaces(self, interfaces_or_fqns, platform = None, template = None):
        """
        Generate code for the given interfaces.

        **Parameters:**
            interfaces_or_fqns  -   A list of transformer groups (typerefs) or FQNs whose code is to be generated.
            platform            -   If a platform is specified then the generated output is for the 
                                    particular platform.  If the platform is not specified then the platform 
                                    specified in the type's "onering.backend" annotation is used.
                                    If this annotation is not specified then the default platform is used. 
                                    Otherwise an error is thrown.
            template            -   Like the platform, specifies the template to use.  The order of resolution
                                    of templates to use is first by the specified one, followed by the 
                                    one specified in its annotation, followed by a default template (if any), 
                                    otherwise an error is thrown.
        """
        for entry in interfaces_or_fqns:
            interface = entry
            if type(interface) in (str, unicode):
                interface = self.context.get_interface(interface)
            orgenutils.generate_interface(interface, self.context, platform, template)

