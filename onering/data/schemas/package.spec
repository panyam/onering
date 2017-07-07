
name = "onering"

version = "0.0.1"
description = """ Core onering schemas.  """

# All schema files to load
inputs = [ "./*.schema" ]

# Extra template directories for use with this package
# template_dirs = [ "../../apigen/data/templates" ]

# This could technically go into a platform specific file but put ht here for now"
platform_es6 = {
    # Specifies an alternative generator class to use.  Defaults to "onering.generators.<platform>.Generator"
    # "generator": { "class": "apigen.generators.es6.Generator", },

    "dependencies": [
        ("request", "*"),
        ("bluebird", "*")
    ],

    # Tells where a particular entity is to be written to based on its FQN
    "exports": [
        ("onering.core.*", "onering.js"),
    ],

    "imports": [ ],

    # A list of resources to be copied to output folder
    "resources": [
        ( "resources/lib/*.js", "lib/" )
    ]
}

