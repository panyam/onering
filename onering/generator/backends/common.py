
def debug_print(*text):
    print "".join(map(str, list(text)))
    return ''

def camel_case(value):
    return value[0].upper() + value[1:]

