
from ipdb import set_trace
import typing
from onering.common import errors, fqns
from onering.typing import core

class Context(object):
    """ A type context/environment that provides bindings between names and types. """
    def __init__(self):
        # All fqn -> type mappings at this level
        self.frames = [{}]

    @property
    def top(self): return self.frames[0]

    @property
    def current(self): return self.frames[-1]

    def push(self): self.frames.append({})
    def pop(self): self.frames.pop()

    def set(self, fqn, thetype, overwrite = False):
        """ Sets a type given its fqn.  """
        fqn = fqns.ensure_fqn(fqn)
        module, last = fqn.parent, fqn.last
        parent = self.ensure(module)
        if last in parent: 
            set_trace()
            assert False
        parent[last] = thetype

    def get(self, fqn):
        fqn = fqns.ensure_fqn(fqn)
        frame = len(self.frames) - 1
        # See which context frame has the start of this fqn
        while frame >= 0 and fqn.parts[0] not in self.frames[frame]:
            frame -= 1
    
        if frame < 0: return None
        curr = self.frames[frame]
        for p in fqn.parts:
            if p not in curr: return None
            curr = curr[p]
        return curr

    def ensure(self, fqn):
        curr = self.current
        if fqn is not None and len(fqn.parts) >= 1:
            for p in fqn.parts:
                if p not in curr:
                    curr[p] = {}
                curr = curr[p]
        return curr

    @property
    def all_types(self) -> typing.List[typing.Tuple[str, core.Type]]:
        """ Returns an iterator to all types along with their FQNs """
        stack = [("", self.frames[0])]
        while stack:
            fqn, node = stack.pop()
            if type(node) is dict:
                for k,v in node.items():
                    newfqn = k if not fqn else fqn + "." + k
                    stack.append((newfqn, v))
            else:
                yield fqn, node

