
import ipdb

def debug_print(*text):
    print "".join(map(str, list(text)))
    return ''

def camel_case(value):
    if value is None: ipdb.set_trace()
    return value[0].upper() + value[1:]

