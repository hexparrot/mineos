"""
    Subclass of Configparser for sectionless configuration files.
    Implements slicing as additional get/set methods.
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import yaml, os
from conf_reader import config_file

class ConfigFS(object):
    def __init__(self):
        self._cache = {}
        self._stat = {}

        self._realfile = {}
        self._style = {}

    def mount(self, style, to_mount, path):
        self._stat[path] = os.stat(to_mount)
        self._cache[path] = self.load(style, to_mount)
        self._realfile[path] = to_mount
        self._style[path] = style

    def data(self, path):
        if os.stat(self._realfile[path]) != self._stat[path]:
            self.mount(self._style[path], self._realfile[path], path)
            
        return self._cache[path]

    def stat(self, path, uid=0, gid=0):
        from fuse import Stat

        stat_result = self._stat[path]
        new_stat = Stat()

        new_stat.st_mode = stat_result.st_mode
        new_stat.st_ino = stat_result.st_ino
        new_stat.st_dev = stat_result.st_dev
        new_stat.st_nlink = stat_result.st_nlink
        new_stat.st_uid = uid
        new_stat.st_gid = gid
        new_stat.st_size = stat_result.st_size
        
        new_stat.st_atime = stat_result.st_atime
        new_stat.st_mtime = stat_result.st_mtime
        new_stat.st_ctime = stat_result.st_ctime

        return new_stat

    def stat_as_directory(self, path, uid=0, gid=0):
        from fuse import Stat
        from stat import S_IFDIR

        stat_result = self._stat[path]
        new_stat = Stat()

        new_stat.st_mode = S_IFDIR | 0555
        new_stat.st_ino = 0
        new_stat.st_dev = 0
        new_stat.st_nlink = 2
        new_stat.st_uid = uid
        new_stat.st_gid = gid
        new_stat.st_size = 4096
        
        new_stat.st_atime = stat_result.st_atime
        new_stat.st_mtime = stat_result.st_mtime
        new_stat.st_ctime = stat_result.st_ctime

        return new_stat

    def stat_for_config(self, path, uid=0, gid=0):
        from fuse import Stat
        from stat import S_IFREG

        stat_result = self._stat[path]
        new_stat = Stat()

        new_stat.st_mode = S_IFREG | 0664
        new_stat.st_ino = 0
        new_stat.st_dev = 0
        new_stat.st_nlink = 1
        new_stat.st_uid = uid
        new_stat.st_gid = gid
        new_stat.st_size = stat_result.st_size
        
        new_stat.st_atime = stat_result.st_atime
        new_stat.st_mtime = stat_result.st_mtime
        new_stat.st_ctime = stat_result.st_ctime

        return new_stat

    def list_dirs(self, path):
        if self._style[path] in ['yaml', 'sections']:
            return self.data(path).keys()

    def list_files(self, path, section=None):
        if self._style[path] == 'sectionless':
            return self.data(path).keys()
        elif self._style[path] == 'flat':
            return self.data(path)
        elif self._style[path] in ['yaml', 'sections']:
            return self.data(path)[section]

    def contents(self, path, prop, section=None):
        if self._style[path] in ['yaml', 'sections']:
            return self.data(path)[section][prop] + '\n'
        elif self._style[path] == 'sectionless':
            return self.data(path)[prop] + '\n'
        elif self._style[path] == 'flat':
            return self.data(path)[prop] + '\n'

    @staticmethod
    def load(style, file_to_load):
        if style == 'yaml':
            with open(file_to_load, 'r') as y:
                return yaml.load(y)
        elif style == 'sections':   
            if os.path.isfile(file_to_load):
                return config_file(file_to_load)[:]
            else:
                raise IOError
        elif style == 'sectionless':
            if os.path.isfile(file_to_load):
                return config_file(file_to_load)[:]
            else:
                raise IOError
        elif style == 'flat':
            with open(file_to_load, 'r') as f:
                return [e.strip() for e in f.readlines()]

