#!/usr/bin/python
"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.5.0a"
__email__ = "wdchromium@gmail.com"

import ConfigParser

class fake_sections(object):
    '''
    This is used to simulate a valid config_parser with sections.
    It is invoked for files such as server.properties.
    '''
    def __init__(self, filepath):
        self.fh = open(filepath)
        self.sechead = '[sectionless]\n'
        
    def readline(self):
        if self.sechead:
            try:
                return self.sechead
            finally:
                self.sechead = None
        else:
            return self.fh.readline()

class config_file(object):
    '''
    Accesses a configuration file of any type--sectioned or sectionless--transparently.
    Current limitations: removes any non-attribute k=v form lines, e.g., comments
    '''
    def __init__(self, filepath=None):
        
        self.filepath = filepath
        self.parser = ConfigParser.ConfigParser(allow_no_value=True)
        self.use_sections = True
        if filepath:
            from os.path import exists
            if not exists(filepath):
                raise IOError('No such config file %s' % filepath)
            else:
                try:
                    self.parser.read(filepath)
                except ConfigParser.MissingSectionHeaderError:
                    self.parser.readfp(fake_sections(filepath))
                    self.use_sections = False

    def __contains__(self, attribute):
        for s in self.parser.sections():
            for k,v in dict(self.parser.items(s)).iteritems():
                if attribute == k:
                    return True
        return False

    def __iter__(self):
        for s in self.parser.sections():
            for k in dict(self.parser.items(s)).iterkeys():
                yield k

    def __str__(self):
        lines = []
        for s in self.parser.sections():
            lines.append('[%s]' % s)
            for k,v in dict(self.parser.items(s)).iteritems():
                lines.append('%s = %s' % (k, v))
        return '\n'.join(lines)

    def iteritems(self):
        for s in self.parser.sections():
            for k in dict(self.parser.items(s)).iterkeys():
                yield (k, self.parser._sections[s][k])

    def add_section(self, section_name):
        if self.use_sections:
            try:
                self.parser.add_section(section_name.strip())
            except ConfigParser.DuplicateSectionError:
                pass
        else:
            raise TypeError('Sections not supported in file %s' % self.filepath)

    def get_attr(self, attribute, section_name='sectionless'):
        try:
            return self.parser._sections[section_name][attribute]
        except KeyError:
            return None

    def set_attr(self, attribute, value, section_name='sectionless'):
        try:
            self.parser.set(section_name, attribute, str(value).strip())
        except ConfigParser.NoSectionError:
            self.parser.add_section(section_name)
            self.parser.set(section_name, attribute, str(value).strip())

    def commit(self):
        if self.use_sections:
            with open(self.filepath, 'wb') as configfile:
                self.parser.write(configfile)
        else:
            with open(self.filepath, "w") as conf:
                for k in self:
                    conf.write("%s=%s\n" % (k.strip(), self.parser._sections['sectionless'][k].strip()))

    def list_attr(self, section_name=None):
        if section_name:
            for k,v in dict(self.parser.items(section_name)).iteritems():
                yield (k, v, section_name)
        else:
            for s in self.parser.sections():
                for k,v in dict(self.parser.items(s)).iteritems():
                    yield (k, v, s)

