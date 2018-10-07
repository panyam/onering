
def ensure_fqn(value):
    if type(value) is not FQN: value = FQN(value, None)
    return value

class FQN(object):
    def __init__(self, name, namespace, ensure_namespaces_are_equal = True):
        name,namespace = (name or "").strip(), (namespace or "").strip()
        self._parts = comps = [n for n in name.split(".") if name.strip()]
        if len(comps) > 1:
            n2 = comps[-1]
            ns2 = ".".join(comps[:-1])
            if ensure_namespaces_are_equal:
                if namespace and ns2 != namespace:
                    assert ns2 == namespace or not namespace, "Namespaces dont match '%s' vs '%s'" % (ns2, namespace)
            name,namespace = n2,ns2

    @property
    def parts(self):
        return self._parts

    @property
    def last(self):
        return self._parts[-1]

    @property
    def parent(self):
        return None if len(self.parts) == 1 else FQN(".".join(self.parts[:-1]), None)

