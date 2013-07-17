"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import ConfigParser

class config_file_sectionless(object):
    def __init__(self, filepath):
        self.filepath = open(filepath, 'r')
        self.fake_section = '[sectionless]\n'

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.filepath.close()
        
    def readline(self):
        if self.fake_section:
            try:
                return self.fake_section
            finally:
                self.fake_section = None
        else:
            return self.filepath.readline()

class config_file(ConfigParser.SafeConfigParser):
    def __init__(self, filepath=None):
        ConfigParser.SafeConfigParser.__init__(self, allow_no_value=True)
        self.filepath = filepath
        self.use_sections = True

        try:
            self.read(self.filepath)
        except ConfigParser.MissingSectionHeaderError:
            self.use_sections = False
            with config_file_sectionless(self.filepath) as cf:
                self.readfp(cf)
        except TypeError:
            pass #if filepath==None

    def __getitem__(self, option):
        if self.use_sections:
            if type(option) in (int,str):
                return dict(self.items(str(option)))
            elif type(option) == slice:
                if type(option.start) == str and type(option.stop) == str:
                    return self.get(option.start, option.stop)
                elif type(option.start) == str and option.stop is None:
                    return dict(self.items(str(option)))
            raise SyntaxError("config_file get syntax: "
                              "var['section'] or "
                              "var['section':'option']")
        else:
            if type(option) in (int,str):
                return self.get('sectionless', str(option))
            elif type(option) == slice:
                if type(option.start) == int and type(option.stop) == int:
                    return dict(self.items('sectionless'))
            raise SyntaxError("config_file get syntax: "
                              "var[:] or "
                              "var['option']")

    def __setitem__(self, option, value):
        if self.use_sections:
            if type(option) == slice:
                if type(option.start) == str and type(option.stop) == str:
                    self.set(option.start, option.stop, str(value))
                    return
            raise SyntaxError("config_file set syntax: "
                              "var['section':'option'] = val")
        else:
            if type(option) in (int,str):
                self.set('sectionless', str(option), str(value))
                return
            raise SyntaxError("config_file set syntax: "
                              "var['section'] = val")

    def commit(self):
        if self.use_sections:
            with open(self.filepath, 'wb') as configfile:
                self.write(configfile)
        else:
            with open(self.filepath, "w") as configfile:
                for k,v in self.items('sectionless'):
                    configfile.write("%s=%s\n" % (k.strip(), v.strip()))
