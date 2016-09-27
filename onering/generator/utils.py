
import ipdb
from typelib import annotations as tlannotations
import importlib
from onering.console.utils import logerror

def evaluate_backend_platforms(annotatable, thering, target_platform = None):
    backend_annotations = []
    if thering.default_platform:
        backend_annotations = [tlannotations.Annotation("onering.backend", None, 
                                    {"platform": thering.default_platform})]
    if annotatable.has_annotation("onering.backend"):
        backend_annotations = [annotatable.get_annotation("onering.backend")]

    if target_platform:
        backend_annotations = [tlannotations.Annotation("onering.backend", None, 
                                {"platform": target_platform, "template": target_template})]

    if not backend_annotations:
        return logerror("Please specify a platform or set a default platform for '%s'" % annotatable.fqn)
    return backend_annotations

def generate_transformers(trans_group, thering, target_platform, target_template):
    # Resolve all transformers first - by now all derived schemas should have been resolved
    trans_group.resolve(thering)

    backend_annotations = evaluate_backend_platforms(trans_group, thering, target_platform)

    for backend_annotation in backend_annotations:
        platform_name = backend_annotation.first_value_of("platform")
        if platform_name not in thering.platform_aliases:
            logerror("Invalid platform: %s" % platform_name)
        platform = thering.platform_aliases[platform_name]
        module_name = ".".join(platform.split(".")[:-1])
        platform_module = importlib.import_module(module_name)
        platform_class = getattr(platform_module, platform.split(".")[-1])
        platform_class(thering, backend_annotation).generate_transformer_group(trans_group)


def generate_schemas(source_typeref, thering, target_platform, target_template):
    """
    Generates one or more schema files for a particular source type.
    """
    # see if the source_typeref has a backend annotation
    if not (source_typeref.is_type and source_typeref.target.constructor == "record"):
        return

    source_type = source_typeref.target
    backend_annotations = evaluate_backend_platforms(source_type, thering, target_platform)

    if not backend_annotations:
        return logerror("Please specify a platform or set a default platform for record: %s" % source_type.fqn)

    for backend_annotation in backend_annotations:
        platform_name = backend_annotation.first_value_of("platform")
        if platform_name not in thering.platform_aliases:
            logerror("Invalid platform: %s" % platform_name)
        platform = thering.platform_aliases[platform_name]
        module_name = ".".join(platform.split(".")[:-1])
        platform_module = importlib.import_module(module_name)
        platform_class = getattr(platform_module, platform.split(".")[-1])
        platform_class(thering, backend_annotation).generate_schema(source_typeref.fqn, source_type)
