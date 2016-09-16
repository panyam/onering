

class OneringException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class NotFoundException(OneringException):
    def __init__(self, entity_type, value):
        self.entity_type = entity_type
        self.value = value
        message = "Not found (%s:%s)" % (entity_type, str(value))
        super(NotFoundException, self).__init__(message)
