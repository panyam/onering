
import os
from onering import errors

def ensure_dir(target_dir):
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

def open_file_for_writing(folder, fname):
    outfile = os.path.join(folder, fname)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return open(outfile, "w")

class DirPointer(object):
    """
    A class to manage a pointer to a current directory and move around.
    Normally with the os.path module there is a global "curdir" that is 
    shared by EVERYTHING - including import_module which means any change
    to the global curdir (via os.chdir) also affects loading of modules 
    dynamically.  We rather want to keep track of directory pointers via
    multiple instances.  Hence this class.
    """
    def __init__(self, curdir = "."):
        self._dirstack = []
        self._current_directory = os.path.abspath(curdir)

    @property
    def curdir(self):
        return self._current_directory

    @curdir.setter
    def curdir(self, value):
        if value.startswith("./") or value.startswith("../"):
            newdir = os.path.abspath(os.path.join(self._current_directory, value))
        else:
            newdir = os.path.abspath(value)
        if not os.path.isdir(newdir):
            raise errors.NotFoundException("dir", newdir)
        else:
            self._current_directory = newdir

    def pushdir(self):
        """
        Pushes the current directory onto the stack so it can be restored later with a popdir.
        """
        self._dirstack.append(self._current_directory)

    def popdir(self):
        self._current_directory = self._dirstack.pop()
        return self._current_directory

    def abspath(self, path):
        if path.startswith("/"):
            # Absolute path
            return path
        elif self.curdir.endswith("/"):
            return os.path.abspath(self.curdir + path)
        else:
            return os.path.abspath(self.curdir + "/" + path)

    def isfile(self, path):
        """
        Tells if the path is a file if it is a relative path.
        """
        return os.path.isfile(self.abspath(path))

    def isdir(self, path):
        """
        Tells if the path is a directory if it is a relative path.
        """
        return os.path.isdir(self.abspath(path))
