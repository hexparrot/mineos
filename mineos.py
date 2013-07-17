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
from conf_reader import config_file
from collections import namedtuple
from binascii import b2a_qp
from string import ascii_letters, digits
from distutils.spawn import find_executable

class mc(object):

    PROCFS_PATHS = ['/proc',
                    '/usr/compat/linux/proc']
    DEFAULT_PATHS = {
        'servers': 'servers',
        'backup': 'backup',
        'archive': 'archive',
        'log': 'log'
        }
    
    def __init__(self, server_name=None, owner=None):
        self._server_name = server_name if self.valid_server_name(server_name) else None
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
        '''
           _homepath will typically go to /home/user, but this can be further
           organized by adding an additional subdirectory, such as:
           self._homepath = os.path.join(self._owner.pwdir, 'minecraft')
           Furthermore, this can be changed to something completely different:
           self._homepath = '/var/games/minecraft'
           Such a change, however, will likely encourage root:root ownership
           to this directory and immediate subdirectories, as multiple users
           will be all sharing the common directories:
           /var/games/minecraft{servers,backup,archive}
        '''
        for p in self.DEFAULT_PATHS.values():
            self._make_directory(os.path.join(self._homepath, p))

    def _set_environment(self):
        if not self.server_name:
            return

        self.server_properties = None
        self.server_config = None
        
        self.env = {}

        self.env['cwd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['servers'], self.server_name)
        self.env['bwd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['backup'], self.server_name)
        self.env['awd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['archive'], self.server_name)
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
        sp.use_sections(False)
        sp.filepath = self.env['sp']

        for k in defaults:
            if k in startup_values:
                defaults[k] = startup_values[k]

        for k,v in defaults.iteritems():
            sp[k] = v

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
                sc[section:attribute] = defaults[section][attribute]

        sc.commit()

    def create(self, properties={}):
        if self.server_name in self.list_servers():
            raise RuntimeWarning('Ignoring command {create}; server already exists.')

        for d in ('cwd', 'bwd', 'awd'):
            self._make_directory(self.env[d])

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

    def kill(self):
        if self.up:
            from signal import SIGTERM
            self._logger.info('Executing command {kill}: %s', self.server_name)
            os.kill(self.java_pid, SIGTERM)
        else:
            raise RuntimeWarning('Ignoring command {kill}: no live process for server %s', self.server_name)

    def archive(self):
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {start}; no server by this name.')

        if self.up:
            self._logger.info('Executing command {archive}: %s', command)
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_archive, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_archive, self.env['cwd'])

    def backup(self):
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {start}; no server by this name.')
        
        if self.up:
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_backup, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_backup, self.env['cwd'])

    def restore(self, steps='now', overwrite=False):
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {restore}; no server by this name.')
        elif self.up:
            raise RuntimeWarning('Ignoring command {restore}; server %s currently up' % self.server_name)
        
        self._load_config(load_backup=True)

        if self.server_properties or self.server_config:
            self._rdiff_backup_steps = steps
            self._rdiff_backup_force = '--force' if overwrite else ''

            self._command_direct(self.command_restore, self.env['cwd'])

            self._load_config(generate_missing=True)
        else:
            raise RuntimeWarning('Ignoring command {restore}; Unable to locate backup')
            
    def _command_direct(self, command, working_directory):
        def demote(user_uid, user_gid):
            def set_ids():
                os.setgid(user_gid)
                os.setuid(user_uid)

            return set_ids

        #FIXME: still must implement sanitization, incl "../'
        from subprocess import check_call

        self._logger.info('Executing as %s from %s: %s', self._owner.pw_name,
                                                         working_directory,
                                                         command)

        current_user = (os.getuid(), os.getgid())

        if current_user == (self._owner.pw_uid, self._owner.pw_gid):
            check_call(command,
                       shell=True,
                       cwd=working_directory)
        else:
            check_call(command,
                       shell=True,
                       cwd=working_directory,
                       preexec_fn=demote(self._owner.pw_uid,
                                         self._owner.pw_gid))

    def _command_stuff(self, stuff_text):
        from subprocess import check_call

        if self.up:
            command = """screen -S %d -p 0 -X eval 'stuff "%s\012"'""" % (self.screen_pid, stuff_text)
            self._logger.info('Executing as %s: %s', self._owner.pw_name,
                                                     command)

            if check_call(command, shell=True):
                self._logger.error('Stuff command returned non-zero error code: "%s"', stuff_text)
        else:
            self._logger.warning('Ignoring command {stuff}; downed server %s: "%s"', self.server_name, stuff_text)
            raise RuntimeWarning('Server must be running to send screen commands')


    def _make_directory(self, path):
        try:
            os.makedirs(path)
        except OSError:
            pass
        else:
            os.chown(path,
                     self._owner.pw_uid,
                     self._owner.pw_gid)

    def _create_logger(self):
        self._make_directory(os.path.join(self._homepath, 'log'))

        try:
            self._logger = logging.getLogger(self.server_name)
            self._logger_fh = logging.FileHandler(os.path.join(self._homepath,
                                                               self.DEFAULT_PATHS['log'],
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
    def server_name(self):
        return self._server_name

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
        if not self.server_config:
            return None
        #FIXME: this doesnt implement profiles--we want profiles!

        required_arguments = {
            'screen_name': 'mc-%s' % self.server_name,
            'screen': find_executable('screen'),
            'java': find_executable('java'),
            'java_xmx': self.server_config['java':'java_xmx'],
            'java_xms': self.server_config['java':'java_xmx'],
            'java_tweaks': self.server_config['java':'java_tweaks'],
            'jar_file': os.path.join(self.env['cwd'], 'minecraft_server.1.6.2.jar'),
            'jar_args': '-nogui'
            }

        if self.server_config.has_option('java','java_xms') :
            required_arguments['java_xms'] = self.server_config['java':'java_xms']

        if any(value is None for value in required_arguments.values()):
            self._logger.error('Cannot construct start command; missing value')
            self._logger.error(str(required_arguments))
        else:
            return '%(screen)s -dmS %(screen_name)s ' \
                   '%(java)s %(java_tweaks)s -Xmx%(java_xmx)sM -Xms%(java_xms)sM ' \
                   '-jar %(jar_file)s %(jar_args)s' % required_arguments

    @property
    def command_archive(self):
        from time import strftime

        required_arguments = {
            'nice': find_executable('nice'),
            'tar': find_executable('tar'),
            'nice_value': 10,
            'archive_filename': os.path.join(self.env['awd'],
                                             'server-%s_%s.tar.gz' % (self.server_name,
                                                                      strftime("%Y-%m-%d_%H:%M:%S"))),
            'cwd': '.' #self.env['cwd']
            }


        if any(value is None for value in required_arguments.values()):
            self._logger.error('Cannot construct archive command; missing value')
            self._logger.error(str(required_arguments))
        else:
            return '%(nice)s -n %(nice_value)s ' \
                   '%(tar)s czf %(archive_filename)s %(cwd)s' % required_arguments

    @property
    def command_backup(self):
        required_arguments = {
            'nice': find_executable('nice'),
            'nice_value': 10,
            'rdiff': find_executable('rdiff-backup'),
            'cwd': self.env['cwd'],
            'bwd': self.env['bwd']
            }

        if any(value is None for value in required_arguments.values()):
            self._logger.error('Cannot construct backup command; missing value')
            self._logger.error(str(required_arguments))
        else:
            return '%(nice)s -n %(nice_value)s ' \
                   '%(rdiff)s %(cwd)s/ %(bwd)s' % required_arguments

    @property
    def command_restore(self):
        required_arguments = {
            'rdiff': find_executable('rdiff-backup'),
            'force': self._rdiff_backup_force if hasattr(self, '_rdiff_backup_force') else '',
            'steps': self._rdiff_backup_steps if hasattr(self, '_rdiff_backup_steps') else 'now',
            'bwd': self.env['bwd'],
            'cwd': self.env['cwd']
            }

        if any(value is None for value in required_arguments.values()):
            self._logger.error('Cannot construct restore command; missing value')
            self._logger.error(str(required_arguments))
        else:
            return '%(rdiff)s %(force)s --restore-as-of %(steps)s ' \
                   '%(bwd)s %(cwd)s' % required_arguments

    @property
    def port(self):
        if not hasattr(self, '_port'):
            try:
                self._port = int(self.server_properties['server-port']) or 0
            except AttributeError:
                self._port = None
        return self._port

    @property
    def ip_address(self):
        if not hasattr(self, '_ip_address'):
            try:
                self._ip_address = self.server_properties['server-ip'] or '0.0.0.0'
            except AttributeError:
                self._ip_address = None
        return self._ip_address

    @property
    def memory(self):
        def sizeof_fmt(num):
            ''' Taken from Fred Cirera, as cited in Sridhar Ratnakumar @
                http://stackoverflow.com/a/1094933/1191579
            '''
            for x in ['bytes','KB','MB','GB','TB']:
                if num < 1024.0:
                    return "%3.2f %s" % (num, x)
                num /= 1024.0
                
        try:
            mem_str = dict(self._list_procfs_entries(self.java_pid, 'status'))['VmRSS']
            mem = int(mem_str.split()[0]) * 1024
            return sizeof_fmt(mem)
        except IOError:
            return '0'

    @property
    def proc_uptime(self):
        raw = self._list_procfs_entries('', 'uptime').next()[0]
        return tuple(float(v) for v in raw.split())

    @property
    def proc_loadavg(self):
        raw = self._list_procfs_entries('', 'loadavg').next()[0]
        return tuple(float(v) for v in raw.split()[:3])

    @property
    def procfs(self):
        if not hasattr(self, '_procfs'):
            for procfs in self.PROCFS_PATHS:
                try:
                    with open(os.path.join(procfs, 'uptime'), 'rb') as procdump:
                        self._procfs = procfs
                        break
                except IOError:
                    continue

        return self._procfs

    ''' generator expressions '''

    def list_servers(self):
        from itertools import chain
        return set(chain(
            self._list_subdirs(os.path.join(self._homepath, self.DEFAULT_PATHS['servers'])),
            self._list_subdirs(os.path.join(self._homepath, self.DEFAULT_PATHS['backup']))
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

    def _list_procfs_entries(self, pid, page):
        with open(os.path.join(self.procfs, str(pid), page)) as proc_status:
            for line in proc_status:
                split = b2a_qp(line).partition(':')
                yield (split[0].strip(), split[2].strip())

    def _list_pids(self):
        """
        Generator: all servers and corresponding processes' pids

        """
        try:        
            pids = frozenset([pid for pid in os.listdir(self.procfs) if pid.isdigit()])
        except TypeError:
            raise IOError('No suitable procfs filesystem found')

        for pid in pids:
            try:
                fh = open(os.path.join(self.procfs, pid, 'cmdline'), 'rb')
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
        pids = set(self._list_pids())
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

    
