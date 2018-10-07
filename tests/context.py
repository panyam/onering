
What does a mix of a Type Context *and* bindings mean?  TypeContext is a "static" map of all types mapped to FQNs.

Bindings how ever are more dynamic because bindings could change based on some execution or analysis function (say type checking or binding evaluation etc).

Second issue is how do FQNs come into play with bindings?  All type variables are *normal* names.  A FQN indicates something in the static scope (in some module).

