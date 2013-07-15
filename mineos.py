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
from binascii import b2a_qp
from string import ascii_letters, digits

class mc(object):

    PROCFS_PATHS = ['/proc',
                    '/usr/compat/linux/proc']
    
    def __init__(self, server_name=None, owner=None):
        if self.valid_server_name(server_name):
            self.server_name = server_name
        self._set_owner(owner)
        self._create_logger()
        self._set_environment()
        self._load_config()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def _set_owner(self, owner):
        from pwd import getpwnam

        if owner is None:
            from getpass import getuser
            owner = getuser()

        self._owner = getpwnam(owner)
        self._homepath = self._owner.pw_dir

    def _set_environment(self):
        if not self.server_name:
            return

        self.server_properties = None
        self.server_config = None
        
        self.env = {}

        self.env['cwd'] = os.path.join(self._homepath, 'servers', self.server_name)
        self.env['bwd'] = os.path.join(self._homepath, 'backup', self.server_name)
        self.env['awd'] = os.path.join(self._homepath, 'archive', self.server_name)
        self.env['sp'] = os.path.join(self.env['cwd'], 'server.properties')
        self.env['sc'] = os.path.join(self.env['cwd'], 'server.config')
        self.env['sp_backup'] = os.path.join(self.env['bwd'], 'server.properties')
        self.env['sc_backup'] = os.path.join(self.env['bwd'], 'server.config')

    def _load_config(self, load_backup=False, generate_missing=False):
        def load_sp():
            self.server_properties = config_file(self.env['sp_backup']) if load_backup else config_file(self.env['sp'])

        def load_sc():
            self.server_config = config_file(self.env['sc_backup']) if load_backup else config_file(self.env['sc'])

        if hasattr(self, 'env'):
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
            raise RuntimeWarning('Ignoring command {start}; no server by this name.')

        if self.up:
            raise RuntimeWarning('Ignoring command {start}; server already up at %s:%s.', self.ip_address, self.port)
        
        if self.port in [s.port for s in self.list_ports_up()]:
            if (self.port, self.ip_address) in [(s.port, s.ip_address) for s in self.list_ports_up()]:
                raise RuntimeWarning('Ignoring command {start}; server already up at %s:%s.', self.ip_address, self.port)
            elif self.ip_address == '0.0.0.0':
                raise RuntimeWarning('Ignoring command {start}; can not listen on (0.0.0.0) if port %s already in use.', self.port)
            elif any(s for s in self.list_ports_up() if s.ip_address == '0.0.0.0'):
                raise RuntimeWarning('Ignoring command {start}; server already listening on ip address (0.0.0.0).')

        self._load_config(generate_missing=True)
        self._logger.info('Executing command {start}; %s@%s:%s', self.server_name, self.ip_address, self.port)

        self._command_direct(self.command_start, self.env['cwd'])

    def archive(self):
        from time import strftime
        archive_filename = 'server-%s_%s.tar.gz' % (self.server_name, strftime("%Y-%m-%d_%H:%M:%S"))
        command = 'nice -n 10 tar czf %s .' % os.path.join(self.env['awd'], archive_filename)
        self._logger.info('Executing command {archive}: %s', command)

    def _command_direct(self, command, working_directory):
        def demote(user_uid, user_gid):
            def set_ids():
                os.setgid(user_gid)
                os.setuid(user_uid)

            return set_ids

        #FIXME: still must implement sanitization, incl "../'
        from subprocess import call

        self._logger.info('Executing as %s from %s: %s', self._owner.pw_name,
                                                         working_directory,
                                                         command)

        current_user = (os.getuid(), os.getgid())

        if current_user == (self._owner.pw_uid, self._owner.pw_gid):
            exitcode = call(command,
                            shell=True,
                            cwd=working_directory)
            if int(exitcode) != 0:
                raise RuntimeError('Command returned exit code %s', exitcode)
        else:
            exitcode = call(command,
                            shell=True,
                            cwd=working_directory,
                            preexec_fn=demote(self._owner.pw_uid,
                                              self._owner.pw_gid))
            if int(exitcode) != 0:
                raise RuntimeError('Command returned exit code %s', exitcode)

    def _command_stuff(self, stuff_text):
        from subprocess import call

        if self.up:
            command = """screen -S %d -p 0 -X eval 'stuff "%s\012"'""" % (self.screen_pid, stuff_text)
            self._logger.info('Executing as %s: %s', self._owner.pw_name,
                                                     command)

            if call(command, shell=True):
                logging.error('Stuff command returned non-zero error code: "%s"', stuff_text)
        else:
            logging.warning('Ignoring command {stuff}; downed server %s: "%s"', self.server_name, stuff_text)
            raise RuntimeWarning('Server must be running to send screen commands')


    def _make_directory(self, path):
        try:
            os.makedirs(path)
        except OSError:
            pass

    def _create_logger(self):
        try:
            os.makedirs(os.path.join(self._homepath, 'log'))
        except OSError:
            pass

        try:
            self._logger = logging.getLogger(self.server_name)
            self._logger_fh = logging.FileHandler(os.path.join(self._homepath,
                                                               'log',
                                                               self.server_name))
        except (TypeError, AttributeError):
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

    def valid_server_name(self, name):
        valid_chars = set('%s%s_.' % (ascii_letters, digits))

        if name is None:
            return False
        if any(c for c in name if c not in valid_chars):
            return False
        elif name.startswith('.'):
            return False
        return True

    ''' properties '''

    @property
    def up(self):
        return self.server_name in self.list_servers_up()

    @property
    def java_pid(self):
        for server, java_pid, screen_pid in self._list_server_pids():
            if self.server_name == server:
                return java_pid
        else:
            return 0

    @property
    def screen_pid(self):
        for server, java_pid, screen_pid in self._list_server_pids():
            if self.server_name == server:
                return screen_pid
        else:
            return 0

    @property
    def command_start(self):
        from distutils.spawn import find_executable

        if not self.server_config:
            return None
        #FIXME: this doesnt implement profiles--we want profiles!

        required_arguments = {
            'screen_name': 'mc-%s' % self.server_name,
            'screen': find_executable('screen'),
            'java': find_executable('java'),
            'java_xmx': self.server_config.get_attr('java_xmx', 'java'),
            'java_xms': self.server_config.get_attr('java_xms', 'java') or
                        self.server_config.get_attr('java_xmx', 'java'),
            'java_tweaks': self.server_config.get_attr('java_tweaks', 'java'),
            'jar_file': os.path.join(self.env['cwd'], 'minecraft_server.1.6.2.jar'),
            'jar_args': '-nogui'
            }

        if all(value is not None for value in required_arguments.values()):
            return '%(screen)s -dmS %(screen_name)s ' \
                   '%(java)s %(java_tweaks)s -Xmx%(java_xmx)sM -Xms%(java_xms)sM ' \
                   '-jar %(jar_file)s %(jar_args)s' % required_arguments
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
            self._list_subdirs(os.path.join(self._homepath, 'servers')),
            self._list_subdirs(os.path.join(self._homepath, 'backup'))
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
            instance = mc(server)
            yield instance_connection(server, instance.port, instance.ip_address)
    
    def _list_subdirs(self, directory):
        try:
            return os.walk(directory).next()[1]
        except StopIteration:
            return []

    def _list_files(self, directory):
        try:
            return os.walk(directory).next()[2]
        except StopIteration:
            return []

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
                serv = re.search(r'SCREEN.*?mc-([\w._]+)', cmdline, re.IGNORECASE)
                try:
                    servers.append(serv.groups()[0])
                except AttributeError:
                    pass

        for serv in servers:
            java = None
            screen = None
            for cmdline, pid in pids:
                if '-jar' in cmdline:
                    if 'screen ' in cmdline.lower() and 'mc-%s ' % serv in cmdline:
                        screen = int(pid)
                    elif '/%s/' % serv in cmdline:
                        java = int(pid)
                if java and screen:
                    break
            yield instance_pids(serv, java, screen)

    
