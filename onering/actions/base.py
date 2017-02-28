
class ActionGroup(object):
    """
    A grouping of actions that can be performed on the context.
    """
    def __init__(self, context):
        self._context = context

    @property
    def context(self):
        return self._context
