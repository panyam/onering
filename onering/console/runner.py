
import ipdb
import shlex

class CommandRunner(object):
    @property
    def children(self):
        return { }

    @property
    def aliases(self): return {}

    def can_run(self, cmd):
        funcname = "do_" + cmd
        return cmd in self.children or cmd in self.aliases or hasattr(self, funcname) 

    def run(self, console, cmd, rest = None, prev = None):
        prev = prev or []
        rest = (rest or "").strip()
        if cmd in self.aliases:
            self.run(console, self.aliases[cmd], rest, prev)
        else:
            funcname = "do_" + cmd
            if hasattr(self, funcname):
                getattr(self, funcname)(console, cmd, rest, prev)
            elif cmd in self.children:
                prev.append(cmd)

                lexer = shlex.shlex(rest)
                try:
                    nextcmd = lexer.next()
                    self.children[cmd].run(console, nextcmd, rest[len(nextcmd):].strip(), prev)
                except StopIteration, si:
                    self.children[cmd].empty_command(console, prev)
            else:
                ipdb.set_trace()
                raise Exception("Command '%s' cannot be handled" % cmd)

    def empty_command(self, console, prev):
        """
        Handles the empty command.
        """
        self.do_man(console, None, "", prev)

    def do_man(self, console, cmd, rest, prev):
        """
        Print the manual for a given list of (comma separted) commands.
        If this list is not given then the manual for ALL commands is printed.
        """
        if not rest:
            scope = "OneRing"
            if prev:
                scope = prev[-1]
            print "%s Commands" % scope
            print "%s-%s" % ("-" * len(scope), "-" * len("Commands"))
        rest = [l.strip() for l in rest.lower().split(",") if l.strip()]
        commands = [(x[3:], getattr(self, x)) for x in dir(self) if x.startswith("do_") and (x[3:] in rest or not rest)]
        for command, func in commands:
            print command
            print "=" * len(command)
            doc = func.__doc__.replace("\n        ", "\n")
            print doc
            print

        if self.children:
            print "subcommands"
            print "-----------"

        for name, command in self.children.iteritems():
            print name
            print "=" * len(name)
            if command.__doc__:
                doc = command.__doc__.replace("\n    ", "\n")
                print doc
                print

