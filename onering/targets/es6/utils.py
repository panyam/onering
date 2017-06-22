
from typelib import core as tlcore
from onering.core import functions as orfuncs

def ensure_modules(outfile, entities):
    visited = set()
    fqns = sorted(set(tuple(x.split(".")[:-1]) for x in entities.keys()))
    for parts in fqns:
        out = ""
        for index,part in enumerate(parts):
            if index > 0: out += "."
            out += part
            if out not in visited:
                if index == 0:
                    outfile.write("var %s = exports.%s = {}\n" % (out, out))
                else:
                    outfile.write("%s = {}\n" % out)
            visited.add(out)

def ensure_namespaces(outfile, namespaces):
    for ns in namespaces:
        if not ns.strip(): continue
        parts = ns.strip().split(".")
        last = None
        for p in parts:
            if not last:
                outfile.write('if (typeof(exports.%s) === "undefined") exports.%s = {};\n' % (p, p))
                outfile.write('var %s = exports.%s\n' % (p,p))
                last = p
            else:
                outfile.write('if (typeof(%s.%s) === "undefined") %s.%s = {};\n' % (last,p,last,p))
                last = last + "." + p
