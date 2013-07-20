"""
    Subclass of Configparser for sectionless configuration files.
    Implements slicing as additional get/set methods.
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
        self.use_sections(True)

        try:
            self.read(self.filepath)
        except ConfigParser.MissingSectionHeaderError:
            self.use_sections(False)
            with config_file_sectionless(self.filepath) as cf:
                self.readfp(cf)
        except TypeError:
            pass #if filepath==None

    def __getitem__(self, option):
        if self._use_sections:
            syntax_error = "config_file get syntax: " \
                           "var[:] or " \
                           "var['section'] or " \
                           "var['section':'option']"
            if type(option) is str:
                return dict(self.items(option))
            elif type(option) is slice:
                if type(option.start) is str:
                    if option.stop is None:
                        try:
                            return dict(self.items(option.start))
                        except ConfigParser.NoSectionError:
                            raise KeyError(option.start)
                    elif type(option.stop) is str:
                        try:
                            return self.get(option.start, option.stop)
                        except ConfigParser.NoSectionError:
                            raise KeyError(option.start)
                        except ConfigParser.NoOptionError:
                            if option.step is None:
                                raise KeyError(option.stop)
                            else:
                                return option.step
                    else:
                        raise TypeError('Inappropriate argument type: %s' % type(option.stop))
                else:
                    from sys import maxint
                    if option.start is 0 and option.stop == maxint:
                        return {sec:dict(self.items(sec)) for sec in self.sections()}
                    else:
                        raise TypeError('Inappropriate argument type: %s' % type(option.start))
            else:
                raise TypeError('Inappropriate argument type: %s' % type(option))
        else:
            syntax_error = "config_file get syntax: " \
                           "var[:] or " \
                           "var['option']"
            if type(option) is str:
                try:
                    return self.get('sectionless', option)
                except ConfigParser.NoOptionError:
                    raise KeyError(option)
            elif type(option) is slice:
                if type(option.start) is str:
                    if option.stop:
                        raise SyntaxError(syntax_error)
                    elif option.stop is None and option.step is None:
                        raise SyntaxError(syntax_error)
                    else:
                        try:
                            return self.get('sectionless', option.start)
                        except ConfigParser.NoOptionError:
                            #__getitem__ cannot return None as default argument
                            #because it cannot distinguish between empty slice arg
                            if option.step is None:
                                raise KeyError(option.start)
                            else:
                                return option.step
                elif type(option.start) is int and type(option.stop) is int:
                    return dict(self.items('sectionless'))
                else:
                    raise TypeError('Inappropriate argument type: %s' % type(option))                        
            else:
                raise TypeError('Inappropriate argument type: %s' % type(option))

    def __setitem__(self, option, value):
        if self._use_sections:
            syntax_error = "config_file set syntax: " \
                           "var['section':'option'] = val"
            if type(option) == slice:
                if type(option.start) is not str:
                    raise TypeError('Inappropriate argument type: %s' % type(option.start))
                elif type(option.stop) is not str:
                    raise TypeError('Inappropriate argument type: %s' % type(option.stop))
                else:
                    if type(value) in (str,int):
                        try:
                            self.set(option.start, option.stop, str(value))
                        except ConfigParser.NoSectionError:
                            raise KeyError(option.start)
                    else:
                        raise TypeError('Value may only be int or string')
            else:
                raise SyntaxError(syntax_error)
        else:
            syntax_error = "config_file set syntax: " \
                           "var['option'] = val"
            if type(option) is str:
                self.set('sectionless', str(option), str(value))
            elif type(option) is slice:
                raise SyntaxError(syntax_error)
            else:
                raise TypeError('Inappropriate argument type: %s' % type(option))

    def __delitem__(self, option):
        if self._use_sections:
            if type(option) == slice:
                if type(option.start) == str and type(option.stop) == str:
                    self.remove_option(option.start, option.stop)
                    return
            raise SyntaxError("config_file del syntax: "
                              "del var['section':'option']")
        else:
            if type(option) in (int,str):
                self.remove_option('sectionless', str(option))
                return
            raise SyntaxError("config_file del syntax: "
                              "del var['option']")

    def commit(self):
        if self._use_sections:
            with open(self.filepath, 'wb') as configfile:
                self.write(configfile)
        else:
            with open(self.filepath, "w") as configfile:
                for k,v in self.items('sectionless'):
                    configfile.write("%s=%s\n" % (k.strip(), v.strip()))

    def use_sections(self, value):
        if value:
            self.remove_section('sectionless')
            self._use_sections = True
        else:
            try:
                self.add_section('sectionless')
            except ConfigParser.DuplicateSectionError:
                pass
            finally:
                self._use_sections = False
            
