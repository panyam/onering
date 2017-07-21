
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
        if type(filename) not in (str, unicode):
            set_trace()
            assert False
        just_opened = False
        if filename not in self._allfiles or self._allfiles[filename].closed:
            just_opened = True
            self._allfiles[filename] = self.open_file(filename)
            self.file_opened(filename, self._allfiles[filename])
        return self._allfiles[filename], just_opened

    def file_opened(self, filename, file):
        """ Called when a file has just been opened for writing. This can be used to 
        write any preambles required onto the file."""
        pass

    def open_file(self, filename):
        """ Open and return a File object with the given filename relative to the output_dir of the target. """
        assert False, "Not yet implemented"

    def close_files(self):
        [f.close() for f in self._allfiles.itervalues()]
        self._allfiles = {}

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

    def load_template(self, template_name, **extra_globals):
        templ = self.generator.package.template_loader.load_from_file(template_name)
        templ.globals.update(extra_globals)
        self.template_loaded(templ)
        return templ

    def load_template_from_string(self, template_string, **extra_globals):
        templ = self.generator.package.template_loader.load_from_string(template_string)
        templ.globals.update(extra_globals)
        self.template_loaded(templ)
        return templ

    def template_loaded(self, templ):
        """ Called after a template has been loaded. """
        templ.globals["breakpoint"] = breakpoint
        templ.globals["context"] = self.generator.context
        templ.globals["package"] = self.generator.package
        templ.globals["importer"] = self.importer
        templ.globals["file"] = self
        return templ

    def close(self):
        """ Close the output file. """
        self.output_file.close()

    def write(self, value, flush = False):
        if not self.closed:
            self.output_file.write(value)
            if flush:
                self.output_file.flush()
        return self

def breakpoint(*args, **kwargs): set_trace()
