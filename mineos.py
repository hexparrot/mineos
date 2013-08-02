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
from conf_reader import config_file
from collections import namedtuple
from distutils.spawn import find_executable
from functools import wraps

def sanitize(fn):
    @wraps(fn)
    def wrapper(self):
        return_func = fn(self)
        if None in self.previous_arguments.values():
            raise RuntimeError('Missing value in %s: %s' % (fn.__name__,str(self.previous_arguments)))
        return return_func
    return wrapper

def server_exists(state):
    def dec(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if (self.server_name in self.list_servers(self.base)) == state:
                fn(self, *args, **kwargs)
            else:
                if state:
                    raise RuntimeWarning('Ignoring {%s}: server not found "%s"' % (fn.__name__,self.server_name))
                else:
                    raise RuntimeWarning('Ignoring {%s}: server already exists "%s"' % (fn.__name__,self.server_name))
        return wrapper
    return dec

def server_up(up):
    def dec(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self.up == up:
                fn(self, *args, **kwargs)
            else:
                raise RuntimeError('Ignoring {%s}: server.up must be %s' % (fn.__name__, up))
        return wrapper
    return dec

class mc(object):

    NICE_VALUE = 10
    DEFAULT_PATHS = {
        'servers': 'servers',
        'backup': 'backup',
        'archive': 'archive',
        'log': 'log',
        'profiles': 'profiles'
        }
    BINARY_PATHS = {
        'rdiff-backup': find_executable('rdiff-backup'),
        'rsync': find_executable('rsync'),
        'screen': find_executable('screen'),
        'java': find_executable('java'),
        'nice': find_executable('nice'),
        'tar': find_executable('tar'),
        'kill': find_executable('kill'),
        'wget': find_executable('wget'),
        }
    
    def __init__(self,
                 server_name,
                 owner=None,
                 base_directory=None):
        
        self._server_name = self.valid_server_name(server_name)
        self._owner, self._base_directory = self.valid_user(owner, base_directory)

        self._set_environment()
        self._load_config()

    def _set_environment(self):
        """
        Sets the most common short-hand paths for the minecraft directories
        and configuration files.

        """
        self.server_properties = None
        self.server_config = None
        self.profile_config = None
        
        self.env = {
            'cwd': os.path.join(self.base, self.DEFAULT_PATHS['servers'], self.server_name),
            'bwd': os.path.join(self.base, self.DEFAULT_PATHS['backup'], self.server_name),
            'awd': os.path.join(self.base, self.DEFAULT_PATHS['archive'], self.server_name),
            'pwd': os.path.join(self.base, self.DEFAULT_PATHS['profiles'])
            }

        self.env.update({
            'sp': os.path.join(self.env['cwd'], 'server.properties'),
            'sc': os.path.join(self.env['cwd'], 'server.config'),
            'pc': os.path.join(self.base, self.DEFAULT_PATHS['profiles'], 'profile.config'),
            'sp_backup': os.path.join(self.env['bwd'], 'server.properties'),
            'sc_backup': os.path.join(self.env['bwd'], 'server.config')
            })

    def _load_config(self, load_backup=False, generate_missing=False):
        """
        Loads server.properties and server.config for a given server.
        With load_backup, /backup/ is referred to rather than /servers/.
        generate_missing will create one and only one missing configuration
        with hard-coded defaults. generate_missing currently should
        only be utilized as a fallback when starting a server.     

        """
        def load_sp():
            self.server_properties = config_file(self.env['sp_backup']) if load_backup else config_file(self.env['sp'])
            self.server_properties.use_sections(False)
            return self.server_properties[:]

        def load_sc():
            self.server_config = config_file(self.env['sc_backup']) if load_backup else config_file(self.env['sc'])
            return self.server_config[:]

        def load_profiles():
            self.profile_config = config_file(self.env['pc'])
            return self.profile_config[:]

        load_sc()
        load_sp()
        load_profiles()

        if generate_missing and not load_backup:
            if self.server_properties[:] and self.server_config[:]:
                pass
            elif self.server_properties[:] and not self.server_config[:]:
                self._create_sc()
                load_sc()
            elif self.server_config[:] and not self.server_properties[:]:
                self._create_sp()
                load_sp()
            else:
                raise RuntimeError('No config files found: server.properties or server.config')   

    @server_exists(True)
    def _create_sp(self, startup_values={}):
        """
        Creates a server.properties file for the server given a dict.
        startup_values is expected to have more options than
        server.properties should have, so provided startup_values
        are only used if they overwrite an option already
        hardcoded in the defaults dict.

        Expected startup_values should match format of "defaults".          

        """
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

        sanitize_integers = set(['server-port',
                                 'max-players',
                                 'gamemode',
                                 'difficulty'])

        for option in sanitize_integers:
            try:
                defaults[option] = int(startup_values[option])
            except (KeyError, ValueError):
                continue

        for option, value in startup_values.iteritems():
            if option not in sanitize_integers:
                defaults[option] = value

        self._command_direct('touch %s' % self.env['sp'], self.env['cwd'])
        with config_file(self.env['sp']) as sp:
            sp.use_sections(False)
            for key, value in defaults.iteritems():
                sp[key] = str(value)

    def _create_sc(self, startup_values={}):
        """
        Creates a server.config file for a server given a dict.
        
        Expected startup_values should match format of "defaults".
        
        """
        defaults = {
            'minecraft': {
                'profile': '',
                },
            'crontabs': {
                'archive': 'none',
                'backup': 'none',
                },
            'onreboot': {
                'restore': False,
                'start': False,
                },
            'java': {
                'java_tweaks': '-server',
                'java_xmx': 256,
                'java_xms': 256,
                }
            }

        sanitize_integers = set([('java', 'java_xmx'),
                                 ('java', 'java_xms'),
                                 ])

        d = defaults.copy()
        d.update(startup_values)

        for section, option in sanitize_integers:
            try:
                d[section][option] = int(startup_values[section][option])
            except (KeyError, ValueError):
                d[section][option] = defaults[section][option]

        self._command_direct('touch %s' % self.env['sc'], self.env['cwd'])
        with config_file(self.env['sc']) as sc:
            for section in d:
                sc.add_section(section)
                for option in d[section]:
                    sc[section:option] = str(d[section][option])

    @server_exists(False)
    def create(self, sc={}, sp={}):
        """
        Creates a server's directories and generates configurations.

        """
        for d in ('cwd', 'bwd', 'awd'):
            self._make_directory(self.env[d])

        sc = sc if type(sc) is dict else {}
        sp = sp if type(sp) is dict else {}
        self._create_sc(sc)
        self._create_sp(sp)
        self._load_config()

    @server_exists(True)
    @server_up(False)
    def start(self):
        """
        Checks if a server is running on its bound IP:PORT
        and if not, starts the screen+java instances.

        """
        if self.port in [s.port for s in self.list_ports_up()]:
            if (self.port, self.ip_address) in [(s.port, s.ip_address) for s in self.list_ports_up()]:
                raise RuntimeError('Ignoring {start}; server already up at %s:%s.' % (self.ip_address, self.port))
            elif self.ip_address == '0.0.0.0':
                raise RuntimeError('Ignoring {start}; can not listen on (0.0.0.0) if port %s already in use.' % self.port)
            elif any(s for s in self.list_ports_up() if s.ip_address == '0.0.0.0'):
                raise RuntimeError('Ignoring {start}; server already listening on ip address (0.0.0.0).')

        self._load_config(generate_missing=True)
        cmd = self.command_start

        if self.list_profiles_md5(self.base)[self.profile]['run_as_md5'] != \
           self._md5sum(self.previous_arguments['jar_file']):
            raise RuntimeError('Assigned jar does not match copy in profile directory') 

        self._command_direct(cmd, self.env['cwd'])

    @server_exists(True)
    @server_up(True)
    def kill(self):
        """
        Kills a server instance by SIGTERM

        """
        self._command_direct(self.command_kill, self.env['cwd'])

    @server_exists(True)
    @server_up(False)
    def archive(self):
        """
        Creates a timestamped, gzipped tarball of the server contents.

        """
        if self.up:
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_archive, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_archive, self.env['cwd'])

    @server_exists(True)
    def backup(self):
        """
        Creates an rdiff-backup of a server.

        """
        if self.up:
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_backup, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_backup, self.env['cwd'])

    @server_exists(True)
    @server_up(False)
    def restore(self, steps='now', overwrite=False):
        """
        Overwrites the /servers/ version of a server with the /backup/.

        """
        from subprocess import CalledProcessError
        
        self._load_config(load_backup=True)

        if self.server_properties or self.server_config:
            self._rdiff_backup_steps = steps
            self._rdiff_backup_force = '--force' if overwrite else ''

            self._make_directory(self.env['cwd'])
            try:
                self._command_direct(self.command_restore, self.env['cwd'])
            except CalledProcessError as e:
                raise RuntimeError(e.message)

            self._load_config(generate_missing=True)
        else:
            raise RuntimeError('Ignoring command {restore}; Unable to locate backup')

    @server_exists(True)
    def prune(self, steps=None):
        """
        Removes old rdiff-backup data/metadata.

        FIXME: Does not do any sanitization on steps.

        """
        self._rdiff_backup_steps = steps
        self._command_direct(self.command_prune, self.env['bwd'])

    def define_profile(self, profile_dict):
        self._make_directory(os.path.join(self.env['pwd']))
        profile_dict['save_as'] = self.valid_filename(os.path.basename(profile_dict['save_as']))
        profile_dict['run_as'] = self.valid_filename(os.path.basename(profile_dict['run_as']))

        with self.profile_config as pc:
            from ConfigParser import DuplicateSectionError
            
            try:
                pc.add_section(profile_dict['name'])
            except DuplicateSectionError:
                pass
            
            for option, value in profile_dict.iteritems():
                if option != 'name':
                    pc[profile_dict['name']:option] = value

    def update_profile(self, profile, expected_md5=None):
        self._make_directory(os.path.join(self.env['pwd'], profile))

        with self.profile_config as pc:
            pc[profile:'save_as'] = self.valid_filename(os.path.basename(pc[profile:'save_as']))
            pc[profile:'run_as'] = self.valid_filename(os.path.basename(pc[profile:'run_as']))

        profile_dict = self.profile_config[profile:]

        if profile_dict['type'] == 'standard_jar':
            old_file_path = os.path.join(self.env['pwd'], profile, profile_dict['save_as'])

            try:
                old_file_md5 = self._md5sum(old_file_path)
            except IOError:
                old_file_md5 = None
            finally:
                if expected_md5 and old_file_md5 == expected_md5:
                    raise RuntimeWarning('Did not download; existing md5 matches expected md5.')

            new_file_path = os.path.join(self.env['pwd'], profile_dict['save_as'])
            
            self._profile_to_download = profile
            self._command_direct(self.command_wget_profile, self.env['pwd'])

            new_file_md5 = self._md5sum(new_file_path)

            if expected_md5 and expected_md5 != new_file_md5:
                raise RuntimeError('Discarding download; new download md5 mismatch with provided hash')
            elif old_file_md5 != new_file_md5:
                from shutil import move
                move(new_file_path, old_file_path)
            else:
                os.unlink(new_file_path) #os.unlink or _command_direct?
                raise RuntimeWarning('Discarding download; new download matches existing md5.')

            with self.profile_config as pc:
                pc[profile:'save_as_md5'] = self._md5sum(old_file_path)
                pc[profile:'run_as_md5'] = self._md5sum(old_file_path)
        else:
            raise NotImplementedError

#actual command execution methods

    @staticmethod
    def _demote(user_uid, user_gid):
        """
        Closure for _command_direct and _command_stuff that changes
        current user to that of self._owner.pd_{uid,gid}

        Usually this will demote, when this script is running as root,
        otherwise it will set its gid and uid to itself.

        """
        def set_ids():
            os.setgid(user_gid)
            os.setuid(user_uid)
        return set_ids

    def _command_direct(self, command, working_directory):
        """
        Opens a subprocess and executes a command as the user
        specified in self._owner.

        #FIXME: still must implement sanitization, including
        uplevel traversal, i.e., "/../'

        """
        from subprocess import check_output, STDOUT
        from shlex import split

        return check_output(split(command),
                            cwd=working_directory,
                            stderr=STDOUT,
                            preexec_fn=self._demote(self.owner.pw_uid, self.owner.pw_gid))

    @server_exists(True)
    @server_up(True)
    def _command_stuff(self, stuff_text):
        """
        Opens a subprocess and stuffs text to an open screen as the user
        specified in self._owner.

        """
        from subprocess import check_call
        from shlex import split

        command = """screen -S %d -p 0 -X eval 'stuff "%s\012"'""" % (self.screen_pid, stuff_text)
        check_call(split(command),
                   preexec_fn=self._demote(self.owner.pw_uid, self.owner.pw_gid))

#validation checks

    @staticmethod
    def valid_server_name(name):
        """
        Checks if a server name is only alphanumerics,
        underscores or dots.

        """
        from string import ascii_letters, digits
        
        valid_chars = set('%s%s_.' % (ascii_letters, digits))

        if not name:
            raise ValueError('Servername must be a string at least 1 length')
        elif any(c for c in name if c not in valid_chars):
            raise ValueError('Servername contains invalid characters')
        elif name.startswith('.'):
            raise ValueError('Servername may not start with "."')
        return name

    @staticmethod
    def valid_filename(fn):
        from string import ascii_letters, digits
        
        valid_chars = set('%s%s-_.' % (ascii_letters, digits))

        if not fn:
            raise ValueError('Filename is empty')
        elif any(c for c in fn if c not in valid_chars):
            raise ValueError('Disallowed characters in filename "%s"' % fn)
        elif fn.startswith('.'):
            raise ValueError('Files should not be hidden: "%s"' % fn)
        return fn

    @staticmethod
    def valid_user(owner=None, base_directory=None):
        from getpass import getuser
        from pwd import getpwnam

        try:
            owner_info = getpwnam(owner)
        except KeyError:
            raise KeyError('No user found %s' % owner)
        except TypeError:
            if owner is None:
                from getpass import getuser
                owner_info = getpwnam(getuser())
            else:
                raise TypeError('Username must be string')

        if base_directory is None:
            base_directory = owner_info.pw_dir
        else:
            normalized = os.path.normpath(base_directory)
            if os.path.exists(normalized):
                base_directory = normalized
            else:
                raise ValueError('base_directory does not exist: %s' % normalized)

        return (owner_info, base_directory)

    ''' properties '''

    @property
    def server_name(self):
        """
        Returns the name of the server.

        """
        return self._server_name

    @property
    def base(self):
        """
        Returns the root path of the server.

        """
        return self._base_directory

    @property
    def owner(self):
        """
        Returns pwd named tuple

        """
        return self._owner

    @property
    def up(self):
        """
        Returns True if the server has a running process.

        """
        return any(s.server_name == self.server_name for s in self.list_servers_up())

    @property
    def java_pid(self):
        """
        Returns the process id of the server's java instance.

        """
        for server, java_pid, screen_pid, base_dir in self.list_servers_up():
            if self.server_name == server:
                return java_pid
        else:
            return None

    @property
    def screen_pid(self):
        """
        Returns the process id of the server's screen instance.

        """
        for server, java_pid, screen_pid, base_dir in self.list_servers_up():
            if self.server_name == server:
                return screen_pid
        else:
            return None

    @property
    def profile(self):
        """
        Returns the profile the server is set to

        """
        try:
            return self.server_config['minecraft':'profile'] or None
        except KeyError:
            return None

    @profile.setter
    def profile(self, value):
        try:
            self.profile_config[value:]
        except KeyError:
            raise KeyError('There is no defined profile by this name in profile.config')
        else:
            with self.server_config as sc:
                from ConfigParser import DuplicateSectionError
                
                try:
                    sc.add_section('minecraft')
                except DuplicateSectionError:
                    pass
                finally:
                    sc['minecraft':'profile'] = str(value).strip()
            
            self._command_direct(self.command_apply_profile, self.env['cwd'])  

    @property
    def port(self):
        """
        Returns the port value from server.properties at time of instance creation.

        """
        try:
            return int(self.server_properties['server-port'])
        except (ValueError, KeyError):
            ''' KeyError: server-port option does not exist
                ValueError: value is not an integer
                exception Note: when value is absent or not an int, vanilla
                adds/replaces the value in server.properties to 25565'''
            return 25565

    @property
    def ip_address(self):
        """
        Returns the ip address value from server.properties at time of instance creation.
        This may return '0.0.0.0' even if that is not the value in the file,
        because it is the effective value vanilla minecraft will run at.

        """
        return self.server_properties['server-ip'::'0.0.0.0'] or '0.0.0.0'
        ''' If server-ip is absent, vanilla starts at *,
            which is effectively 0.0.0.0 and
            also adds 'server-ip=' to server.properties.'''

    @property
    def memory(self):
        """
        Returns the amount of memory the java instance is using (VmRSS)

        """
        def sizeof_fmt(num):
            ''' Taken from Fred Cirera, as cited in Sridhar Ratnakumar @
                http://stackoverflow.com/a/1094933/1191579
            '''
            for x in ['bytes','KB','MB','GB','TB']:
                if num < 1024.0:
                    return "%3.2f %s" % (num, x)
                num /= 1024.0
                
        from procfs_reader import entries
          
        try:
            mem_str = dict(entries(self.java_pid, 'status'))['VmRSS']
            mem = int(mem_str.split()[0]) * 1024
            return sizeof_fmt(mem)
        except IOError:
            return '0'
        
    @property
    def ping(self):
        import socket

        server_ping = namedtuple('ping', ['protocol_version',
                                          'server_version',
                                          'motd',
                                          'players_online',
                                          'max_players'])

        if self.up:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.ip_address, self.port))
                s.send('\xfe'      #1
                       '\x01'      #2
                       '\xfa'      #3
                       '\x00\x06'  #4
                       '\x00\x6d\x00\x69\x00\x6e\x00\x65\x00\x6f\x00\x73'
                       '\x00\x19'  #6
                       '\x49'      #7
                       '\x00\x09'  #8
                       '\x00\x6c\x00\x6f\x00\x63\x00\x61\x00\x6c\x00\x68'
                       '\x00\x6f\x00\x73\x00\x74'
                       '\x00\x00\x63\xdd') #10

                d = s.recv(1024)
                s.shutdown(socket.SHUT_RDWR)
            except socket.error:
                return server_ping(None,None,self.server_properties['motd'::''],
                                   '-1',self.server_properties['max-players'])
            finally:
                s.close()

            assert d[0] == '\xff'

            segments = d[3:].decode('utf-16be')

            if segments[0] == u'\xa7': #1.5.2
                return server_ping(*[str(c) for c in segments[3:].split('\x00')])
            else:
                return server_ping(*[str(c) for c in segments.split(u'\xa7')])
        else:
            if self.server_name in self.list_servers(self.base):
                return server_ping(None,None,self.server_properties['motd'::''],
                                   '0',self.server_properties['max-players'])
            else:
                raise RuntimeWarning('Server not found "%s"' % self.server_name)

    @property
    def sp(self):
        return self.server_properties[:]

    @property
    def sc(self):
        return self.server_config[:]        

# shell command constructor properties

    @property
    def previous_arguments(self):
        try:
            return self._previous_arguments
        except AttributeError:
            return {}

    @property
    @sanitize
    def command_start(self):
        """
        Returns the actual command used to start up a minecraft server.

        """
        required_arguments = {
            'screen_name': 'mc-%s' % self.server_name,
            'screen': self.BINARY_PATHS['screen'],
            'java': self.BINARY_PATHS['java'],
            'java_xmx': self.server_config['java':'java_xmx'],
            'java_xms': self.server_config['java':'java_xmx'],
            'java_tweaks': self.server_config['java':'java_tweaks'],
            'jar_args': '-nogui'
            }

        try:
            jar_file = self.valid_filename(self.profile_config[self.profile:'run_as'])
            required_arguments['jar_file'] = os.path.join(self.env['cwd'], jar_file)
            required_arguments['jar_args'] = self.profile_config[self.profile:'jar_args':'']
        except (TypeError,ValueError):
            required_arguments['jar_file'] = None
            required_arguments['jar_args'] = None        

        try:
            java_xms = self.server_config['java':'java_xms']
        except KeyError:
            pass
        else:
            if java_xms.strip():
                self.server_config['java':'java_xms'] = java_xms.strip()                

        self._previous_arguments = required_arguments
        return '%(screen)s -dmS %(screen_name)s ' \
               '%(java)s %(java_tweaks)s -Xmx%(java_xmx)sM -Xms%(java_xms)sM ' \
               '-jar %(jar_file)s %(jar_args)s' % required_arguments

    @property
    @sanitize
    def command_archive(self):
        """
        Returns the actual command used to archive a minecraft server.
        Note, this command should be run from the /servers/[servername] directory.

        """
        from time import strftime

        required_arguments = {
            'nice': self.BINARY_PATHS['nice'],
            'tar': self.BINARY_PATHS['tar'],
            'nice_value': self.NICE_VALUE,
            'archive_filename': os.path.join(self.env['awd'],
                                             'server-%s_%s.tar.gz' % (self.server_name,
                                                                      strftime("%Y-%m-%d_%H:%M:%S"))),
            'cwd': '.'
            }

        self._previous_arguments = required_arguments
        return '%(nice)s -n %(nice_value)s ' \
               '%(tar)s czf %(archive_filename)s %(cwd)s' % required_arguments

    @property
    @sanitize
    def command_backup(self):
        """
        Returns the actual command used to rdiff-backup a minecraft server.

        """
        required_arguments = {
            'nice': self.BINARY_PATHS['nice'],
            'nice_value': self.NICE_VALUE,
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'cwd': self.env['cwd'],
            'bwd': self.env['bwd']
            }

        self._previous_arguments = required_arguments
        return '%(nice)s -n %(nice_value)s ' \
               '%(rdiff)s %(cwd)s/ %(bwd)s' % required_arguments

    @property
    @sanitize
    def command_kill(self):
        """
        Returns the command to kill a pid

        """
        required_arguments = {
            'kill': self.BINARY_PATHS['kill'],
            'pid': self.screen_pid
            }

        self._previous_arguments = required_arguments
        return '%(kill)s %(pid)s' % required_arguments

    @property
    @sanitize
    def command_restore(self):
        """
        Returns the actual command used to rdiff restore a minecraft server.

        """
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'force': self._rdiff_backup_force if hasattr(self, '_rdiff_backup_force') else '',
            'steps': self._rdiff_backup_steps if hasattr(self, '_rdiff_backup_steps') else 'now',
            'bwd': self.env['bwd'],
            'cwd': self.env['cwd']
            }

        self._previous_arguments = required_arguments
        return '%(rdiff)s %(force)s --restore-as-of %(steps)s ' \
               '%(bwd)s %(cwd)s' % required_arguments

    @property
    @sanitize
    def command_prune(self):
        """
        Returns the actual command used to rdiff prune minecraft backups.

        """
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'steps': None,
            'bwd': self.env['bwd']
            }

        try:
            required_arguments['steps'] = self._rdiff_backup_steps
        except AttributeError:
            pass
        else:
            if type(required_arguments['steps']) is int:
                required_arguments['steps'] = '%sB' % required_arguments['steps']

        self._previous_arguments = required_arguments
        return '%(rdiff)s --force --remove-older-than %(steps)s %(bwd)s' % required_arguments

    @property
    @sanitize
    def command_list_increments(self):
        """
        Returns the number of increments found at the backup dir

        """
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'bwd': self.env['bwd']
            }

        self._previous_arguments = required_arguments
        return '%(rdiff)s --list-increments %(bwd)s' % required_arguments

    @property
    @sanitize
    def command_wget_profile(self):
        """
        Returns the command to download a new file

        """
        required_arguments = {
            'wget': self.BINARY_PATHS['wget'],
            'newfile': os.path.join(self.env['pwd'],
                                    self.profile_config[self._profile_to_download:'save_as']),
            'url': self.profile_config[self._profile_to_download:'url']
            }

        self._previous_arguments = required_arguments
        return '%(wget)s -O %(newfile)s %(url)s' % required_arguments

    @property
    @sanitize
    def command_apply_profile(self):
        """
        Returns the command to copy profile files
        into the live working directory.

        """       
        required_arguments = {
            'profile': self.profile,
            'rsync': self.BINARY_PATHS['rsync'],
            'pwd': os.path.join(self.env['pwd']),
            'exclude': '',
            'cwd': '.'
            }

        try:
            files_to_exclude_str = self.profile_config[self.profile:'ignore']
        except (TypeError,KeyError):
            raise RuntimeError('Missing value in apply_profile command: %s' % str(required_arguments))
        else:
            if ',' in files_to_exclude_str:
                files = [f.strip() for f in files_to_exclude_str.split(',')]
            else:
                files = [f.strip() for f in files_to_exclude_str.split()]
            required_arguments['exclude'] = ' '.join("--exclude='%s'" % f for f in files)

        self._previous_arguments = required_arguments
        return '%(rsync)s -a %(exclude)s %(pwd)s/%(profile)s/ %(cwd)s' % required_arguments

#generator expressions

    @classmethod
    def list_servers(cls, base_directory=None):
        """
        Lists all directories in /servers/ and /backup/.
        Note, not all listings may be servers.

        """        
        from itertools import chain

        if base_directory is None:
            base_directory = cls.valid_user()[1]
        
        return set(chain(
            cls.list_subdirs(os.path.join(base_directory, cls.DEFAULT_PATHS['servers'])),
            cls.list_subdirs(os.path.join(base_directory, cls.DEFAULT_PATHS['backup']))
            ))

    @classmethod
    def list_ports_up(cls):
        """
        Returns IP address and port used by all live,
        running instances of Minecraft.

        """
        instance_connection = namedtuple('instance_connection', 'server_name port ip_address')
        for name, java, screen, base_dir in cls.list_servers_up():
            instance = cls(name, base_directory=base_dir)
            yield instance_connection(name, instance.port, instance.ip_address)

    def list_increments(self):
        """
        Returns a tuple of the timestamp of the most current mirror
        and a list of all the increment files found.

        """
        from subprocess import CalledProcessError

        incs = namedtuple('increments', 'current_mirror increments')
        
        try:
            output = self._command_direct(self.command_list_increments, self.env['bwd'])
            assert output is not None
        except (CalledProcessError, AssertionError):
            return incs('', [])
        
        output_list = output.split('\n')
        increment_string = output_list.pop(0)
        output_list.pop() #empty newline throwaway
        current_string = output_list.pop()

        '''num_increments = iter(int(p) for p in increment_string.split() if p.isdigit()).next()'''
        timestamp = current_string.partition(':')[-1].strip()
        
        return incs(timestamp, [d.strip() for d in output_list])

    @classmethod
    def list_servers_up(cls):
        """
        Generator: screen and java pid info for all running servers
        
        """
        from procfs_reader import pid_cmdline
        
        pids = dict(pid_cmdline())
        instance_pids = namedtuple('instance_pids', 'server_name java_pid screen_pid base_dir')
        
        def name_base():
            import re

            for cmdline in pids.itervalues():
                if 'screen' in cmdline.lower():
                    serv = re.search(r'SCREEN.*?mc-([\w._]+).*?-jar ([\w._/]+)\1', cmdline, re.IGNORECASE)
                    try:
                        yield (serv.groups()[0], serv.groups()[1]) #server_name, base_dir
                    except AttributeError:
                        continue

        for name, base in name_base():
            java = None
            screen = None

            for pid, cmdline in pids.iteritems():
                if '-jar' in cmdline:
                    if 'screen' in cmdline.lower() and 'mc-%s' % name in cmdline:
                        screen = int(pid)
                    elif '/%s/' % name in cmdline:
                        java = int(pid)
                    if java and screen:
                        break
            yield instance_pids(name, java, screen, os.path.dirname(os.path.dirname(base)))
            '''dirname x2 truncates /servers/ from the string.  all these scripts operate
            on the assumption of child directories anyway, so this is hardcoded'''

    @classmethod
    def list_profiles(cls, base_directory=None):
        if base_directory is None:
            base_directory = cls.valid_user()[1]

        pc = config_file(os.path.join(base_directory, 'profiles', 'profile.config'))
        return pc[:]

    @classmethod
    def list_profiles_md5(cls, base_directory=None):
        if base_directory is None:
            base_directory = cls.valid_user()[1]

        md5s = {}

        for profile, opt_dict in cls.list_profiles(base_directory).iteritems():
            path = os.path.join(base_directory, 'profiles', profile)
            md5s[profile] = {}
            md5s[profile]['save_as_md5'] = cls._md5sum(os.path.join(path,opt_dict['save_as']))
            md5s[profile]['run_as_md5'] = cls._md5sum(os.path.join(path,opt_dict['run_as']))
            
        return md5s

    @staticmethod
    def _md5sum(filepath):
        from hashlib import md5
        with open(filepath, 'rb') as infile:
            m = md5()
            m.update(infile.read())
            return m.hexdigest()

#filesystem functions

    def _make_directory(self, path, do_raise=False):
        """
        Creates a directory and chowns it to self._owner.
        Fails silently.

        """
        try:
            os.makedirs(path)
        except OSError:
            if do_raise: raise
        else:
            os.chown(path, self.owner.pw_uid, self.owner.pw_gid)

    def copytree(self, src, dst, ignore=None):
        """
        Recursively copies a directory and its contents.
        Keyword Arguments:
        src -- source directory
        dst -- destination directory
        ignore -- shutil.ignore_patterns object
        Modified version of http://docs.python.org/library/shutil.html
        
        """
        from shutil import copystat, copy2, Error
        
        names = os.listdir(src)
        self._make_directory(dst)
        
        errors = []
        
        if ignore is not None:
            ignored_names = ignore(src, names)
        else:
            ignored_names = set()

        for name in names:
            if name in ignored_names:
                continue
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if os.path.isdir(srcname):
                    self.copytree(srcname, dstname, ignore)
                else:
                    copy2(srcname, dstname)
                    os.chown(dstname,
                             self.owner.pw_uid,
                             self.owner.pw_gid)
            except (IOError, os.error) as why:
                errors.append((srcname, dstname, str(why)))
            except Error as err:
                errors.extend(err.args[0])
        try:
            copystat(src, dst)
        except OSError as why:
            errors.extend((src, dst, str(why)))

    @staticmethod
    def list_subdirs(directory):
        """
        Returns a list of all subdirectories of a path.

        """
        try:
            return os.walk(directory).next()[1]
        except StopIteration:
            return []

    @staticmethod
    def list_files(directory):
        """
        Returns a list of all files in a path (no recursion).

        """
        try:
            return os.walk(directory).next()[2]
        except StopIteration:
            return []
