
class FQN(object):
    def __init__(self, name, namespace, ensure_namespaces_are_equal = True):
        name,namespace = (name or "").strip(), (namespace or "").strip()
        comps = name.split(".")
        if len(comps) > 1:
            n2 = comps[-1]
            ns2 = ".".join(comps[:-1])
            if ensure_namespaces_are_equal:
                if namespace and ns2 != namespace:
                    assert ns2 == namespace or not namespace, "Namespaces dont match '%s' vs '%s'" % (ns2, namespace)
            name,namespace = n2,ns2
        fqn = None
        if namespace and name:
            fqn = namespace + "." + name
        elif name:
            fqn = name
        self._name = name
        self._namespace = namespace
        self._fqn = fqn

    @property
    def parts(self):
        return self._name, self._namespace, self._fqn

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace

    @property
    def fqn(self):
        return self._fqn

