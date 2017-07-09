
import os
from ipdb import set_trace
from onering.utils.misc import FQN
from onering.utils.dirutils import open_file_for_writing

class Generator(object):
    def __init__(self, context, package, output_dir):
        self.context = context
        self.package = package
        self.output_dir = output_dir
        self._allfiles = {}
        self._openfiles = set()
        context.global_module.ensure_parents()

    def generate(self, context):
        """ Generates all artifacts for a particular platform. """
        # Close all the files we have open
        pass

    def finalise(self):
        """ Calls just before closing of all files that are being written to. """
        pass

    def ensure_file(self, filename):
        if filename not in self._allfiles or self._allfiles[filename].closed:
            self._allfiles[filename] = self.open_file(filename)
        return self._allfiles[filename]

    def open_file(self, filename):
        """ Open and return a File object with the given filename relative to the output_dir of the target. """
        assert False, "Not yet implemented"

    def close_files(self):
        [f.close() for f in self._allfiles.itervalues()]
        self._allfiles = {}

    def load_template(self, template_name, **extra_globals):
        templ = self.package.template_loader.load_from_file(template_name)
        templ.globals.update(extra_globals)
        self.template_loaded(templ)
        return templ

    def load_template_from_string(self, template_string, **extra_globals):
        templ = self.package.template_loader.load_from_string(template_string)
        templ.globals.update(extra_globals)
        self.template_loaded(templ)
        return templ

    def template_loaded(self, templ):
        """ Called after a template has been loaded. """
        templ.globals["context"] = self.context
        templ.globals["package"] = self.package
        return templ

class File(object):
    """ A file to which a collection of entries are written to. """
    def __init__(self, generator, fname):
        self.generator = generator
        self.filename = fname
        self.output_file = open_file_for_writing(self.output_dir, self.filename)

    @property
    def output_dir(self):
        return self.generator.output_dir

    @property
    def output_path(self):
        return os.path.abspath(os.path.join(self.output_dir, self.filename))

    @property
    def closed(self):
        return self.output_file.closed

    def close(self):
        """ Close the output file. """
        self.output_file.close()

    def write(self, value, flush = False):
        if not self.closed:
            self.output_file.write(value)
            if flush:
                self.output_file.flush()
        return self
