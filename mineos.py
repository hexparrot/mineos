#!/usr/bin/env python2.7
"""
A python script to manage minecraft servers.
Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import os
import logging
from conf_parse import config_file
from collections import namedtuple

class mineos(object):

    DEFAULT_PATHS = {
        'live': r'z:\mineos\servers',
        'backup': r'z:\mineos\backup',
        'archive': r'z:\mineos\archive',
        'logging': r'z:\mineos\log'
        }

    PROCFS_PATHS = ['/proc',
                     '/usr/compat/linux/proc']
    
    def __init__(self, server_name=None):
        self.server_name = server_name
        self._create_logger()
        self._set_environment()
        self._load_config()

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass

    def _set_environment(self):
        if not self.server_name:
            return

        self.server_properties = None
        self.server_config = None
        
        self.env = {}

        self.env['cwd'] = os.path.join(self.DEFAULT_PATHS['live'], self.server_name)
        self.env['bwd'] = os.path.join(self.DEFAULT_PATHS['backup'], self.server_name)
        self.env['awd'] = os.path.join(self.DEFAULT_PATHS['archive'], self.server_name)
        self.env['sp'] = os.path.join(self.env['cwd'], 'server.properties')
        self.env['sc'] = os.path.join(self.env['cwd'], 'server.config')
        self.env['sp_backup'] = os.path.join(self.env['bwd'], 'server.properties')
        self.env['sc_backup'] = os.path.join(self.env['bwd'], 'server.config')        

    def _load_config(self, load_backup=False, generate_missing=False):
        def load_sp():
            self.server_properties = config_file(self.env['sp_backup']) if load_backup else config_file(self.env['sp'])

        def load_sc():
            self.server_config = config_file(self.env['sc_backup']) if load_backup else config_file(self.env['sc'])

        if self.env:
            if not self.server_config:
                try:
                    load_sc()
                except IOError:
                    pass

            if not self.server_properties:
                try:
                    load_sp()
                except IOError:
                    pass

            if generate_missing and not load_backup:
                if self.server_properties and self.server_config:
                    pass
                elif self.server_properties and not self.server_config:
                    self._create_sc()
                    self._load_sc()
                elif self.server_config and not self.server_properties:
                    self._create_sp()
                    self._load_sp()
                else:
                    raise RuntimeError('No config files found: server.properties or server.config')               

    def _create_sp(self, startup_values={}):
        defaults = {
            'server-port': 25565,
            'max-players': 20,
            'level-seed': '',
            'gamemode': 0,
            'difficulty': 1,
            'level-type': 'DEFAULT',
            'level-name': 'world',
            'max-build-height': 256,
            'generate-structures': 'false',
            'generator-settings': '',
            'server-ip': '0.0.0.0',
            }

        sp = config_file()
        sp.use_sections = False
        sp.filepath = self.env['sp']

        for k in defaults:
            if k in startup_values:
                defaults[k] = startup_values[k]

        for k,v in defaults.iteritems():
            sp.set_attr(k,v)

        sp.commit()

    def _create_sc(self, startup_values={}):
        defaults = {
                'crontabs': {
                    'archive': 'none',
                    'backup': 'none',
                    },
                'onreboot': {
                    'restore': False,
                    'start': False,
                    },
                'java': {
                    'java_tweaks': startup_values.get('java_tweaks', '-server'),
                    'java_xmx': startup_values.get('java_xmx', 256),
                    'java_xms': startup_values.get('java_xms', startup_values.get('java_xmx', 256)),
                    }
            }
        
        sc = config_file()
        sc.filepath = self.env['sc']

        sanitize_integers = set(['server-port', 'max-players', 'java_xmx', 'java_xms', 'gamemode', 'difficulty'])
        for k,v in startup_values.iteritems():
            if k in sanitize_integers:
                try:
                    startup_values[k] = int(v)
                except ValueError:
                    del startup_values[k]
            else:
                startup_values[k] = ''.join(c for c in startup_values[k] if c.isalnum)

        for section in defaults:
            sc.add_section(section)
            for attribute in defaults[section]:
                sc.set_attr(attribute, defaults[section][attribute], section)

        sc.commit()

    def create(self, properties={}):
        if self.server_name in self.list_servers():
            raise RuntimeWarning('Ignoring command {create}; server already exists.')

        for d in ('cwd', 'bwd', 'awd'):
            try:
                os.makedirs(self.env[d])
            except OSError:
                pass

        properties = properties if type(properties) is dict else {}
        self._create_sc(properties)
        self._create_sp(properties)
        self._load_config()
    
    def start(self):
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {start}; no server by this name.' % self.server_name)
        
        if self.port in [s.port for s in self.list_ports_up()]:
            if (self.port, self.ip_address) in [(s.port, s.ip_address) for s in self.list_ports_up()]:
                raise RuntimeWarning('Ignoring command {start}; server already up at %s:%s.' % (self.ip_address, self.port))
            elif self.ip_address == '0.0.0.0':
                raise RuntimeWarning('Ignoring command {start}; can not listen on (0.0.0.0) if port %s already in use.' % self.port)
            elif any(s for s in self.list_ports_up() if s.ip_address == '0.0.0.0'):
                raise RuntimeWarning('Ignoring command {start}; server already listening on ip address (0.0.0.0).')

        self._load_config(generate_missing=True)
        self._logger.info('Executing command {start}; server %s:%s', self.ip_address, self.port)

    def _make_directory(self, path):
        try:
            os.makedirs(self.DEFAULT_PATHS['logging'])
        except OSError:
            pass

    def _create_logger(self):
        try:
            os.makedirs(self.DEFAULT_PATHS['logging'])
        except OSError:
            pass

        try:
            self._logger = logging.getLogger(self.server_name)
            self._logger_fh = logging.FileHandler(os.path.join(self.DEFAULT_PATHS['logging'], self.server_name))
        except TypeError:
            self._logger = None
            self._logger_fh = None
        else:
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s: %(message)s')
            self._logger_fh.setFormatter(formatter)
            self._logger.addHandler(self._logger_fh)
            self._logger.setLevel(logging.DEBUG)

    def _destroy_logger(self):
        if self._logger_fh:
            self._logger_fh.close()

    ''' properties '''

    @property
    def cmdline(self):
        from distutils.spawn import find_executable

        if not self.server_config:
            return None
        #this doesnt implement profiles--we want profiles!

        required_arguments = {
            'screen_name': 'mc-%s' % self.server_name,
            'screen': find_executable('screen'),
            'java': find_executable('java'),
            'java_xmx': self.server_config.get_attr('java_xmx', 'java'),
            'java_xms': self.server_config.get_attr('java_xms', 'java') or
                        self.server_config.get_attr('java_xmx', 'java'),
            'java_tweaks': self.server_config.get_attr('java_tweaks', 'java'),
            }

        if all(value is not None for value in required_arguments.values()):
            return '%(screen)s -dmS %(screen_name)s ' \
                   '%(java)s %(java_tweaks)s -Xmx%(java_xmx)s -Xms%(java_xms)s ' \
                   '-jar JAR_FILE_HERE JAR_ARGS_HERE' % arguments
        else:
            self._logger.error('Cannot construct start command; missing value')
            self._logger.error(str(required_arguments))
            return None

    @property
    def port(self):
        if not hasattr(self, '_port'):
            try:
                self._port = int(self.server_properties.get_attr('server-port')) or 0
            except AttributeError:
                self._port = None
        return self._port

    @property
    def ip_address(self):
        if not hasattr(self, '_ip_address'):
            try:
                self._ip_address = self.server_properties.get_attr('server-ip') or '0.0.0.0'
            except AttributeError:
                self._ip_address = None
        return self._ip_address

    ''' generator expressions '''

    def list_servers(self):
        from itertools import chain
        return set(chain(
            self._list_subdirs(self.DEFAULT_PATHS['live']),
            self._list_subdirs(self.DEFAULT_PATHS['backup'])
            ))

    def list_servers_up(self):
        """
        Generator: all servers which were started with "mc-SERVER" name.

        """
        for instance in self._list_server_pids():
            yield instance.server_name

    def list_ports_up(self):
        instance_connection = namedtuple('instance_connection', 'server_name port ip_address')
        for server in self.list_servers_up():
            instance = mineos(server)
            yield instance_connection(server, instance.port, instance.ip_address)
    
    def _list_subdirs(self, directory):
        return os.walk(directory).next()[1]

    def _list_files(self, directory):
        return os.walk(directory).next()[2]

    def _list_pids(self):
        """
        Generator: all servers and corresponding processes' pids

        """
        if not hasattr(self, '_procfs'):
            for procfs in self.PROCFS_PATHS:
                try:
                    with open(os.path.join(procfs, 'uptime'), 'rb') as procdump:
                        self._procfs = procfs
                        break
                except IOError:
                    continue

        try:        
            pids = frozenset([pid for pid in os.listdir(self._procfs) if pid.isdigit()])
        except TypeError:
            raise IOError('No suitable procfs filesystem found')

        for pid in pids:
            try:
                fh = open(os.path.join(self._procfs, pid, 'cmdline'), 'rb')
                cmdline = fh.read()
            except IOError:
                continue
            else:
                if cmdline:
                    yield (b2a_qp(cmdline).replace('=00', ' ').replace('=\n', ''), pid)
            finally:
                fh.close()

    def _list_server_pids(self):
        """
        Generator: screen and java pid info for all running servers
        Returns: (server_name, java_pid, screen_pid)
        
        """
        import re

        instance_pids = namedtuple('instance_pids', 'server_name java_pid screen_pid')
        pids = frozenset(self._list_pids())
        servers = []
        retval = {}
        
        for cmdline, pid in pids:
            if 'screen' in cmdline.lower():
                serv = re.match(r'SCREEN.*?mc-([\w._]+)', cmdline, re.IGNORECASE)
                try:
                    servers.append(serv.groups()[0])
                except AttributeError:
                    pass

        for serv in servers:
            java = None
            screen = None
            for cmdline, pid in pids:
                if '-jar' in cmdline:
                    if cmdline.lower().startswith('screen ') and 'mc-%s ' % serv in cmdline:
                        screen = pid
                    elif '/%s/' % serv in cmdline:
                        java = pid
                if java and screen:
                    break
            yield instance_pids(serv, java, screen)

    
