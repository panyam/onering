
import ipdb

class ORException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class ValidationError(ORException): pass

