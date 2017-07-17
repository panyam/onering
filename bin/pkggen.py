#!/usr/bin/env python

"""
Generates a package given the path to a package.spec.
"""
import sys
import os
import json
import ipdb
import pprint

from onering.packaging import packages
from onering.core import context as orcontext
from onering.actions import dirs as diractions
from onering.utils import dirutils

def exit_with_error(parser, msg):
    if msg:
        print ; print msg ; print
    print parser.format_help()
    parser.exit(1)

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-p", "--package", dest = "package_path", help = "Folder containing the package.spec file or the path to the package.spec file.")
parser.add_option("-o", "--output_dir", dest = "output_dir", help = "Root output folder where all generated schemas, models, transformers, interfaces and clients are written to", default = None)
parser.add_option("-t", "--target_platform", dest = "target_platform", help = "The target platform for which artifacts are to be generted.  eg 'es6', 'swift', 'java', 'python'", default = "es6")

options,args = parser.parse_args()

if options.output_dir is None:
    options.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../output")
else:
    dirutils.ensure_dir(options.output_dir)

if not options.package_path:
    exit_with_error(parser, "Package path required")
else:
    if os.path.isdir(options.package_path):
        options.package_path = os.path.join(options.package_path, "package.spec")
    if not os.path.isfile(options.package_path):
        exit_with_error(parser, "Invalid package spec path: %d" % options.package_spec)

context = orcontext.OneringContext()
package = context.load_package(options.package_path)
# package.select_platform(options.target_platform)
package.select_platform("java")

pkgdir = os.path.abspath(os.path.join(options.output_dir, package.name))
package.copy_resources(context, pkgdir)

generator = package.get_generator(context, pkgdir)
generator.generate()
