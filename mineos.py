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
import procfs_reader
import urllib2
from conf_reader import config_file
from collections import namedtuple
from string import ascii_letters, digits
from distutils.spawn import find_executable

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
        }
    
    def __init__(self, server_name=None, owner=None, group=None):
        if self.valid_server_name(server_name):
            self._server_name = server_name
        elif server_name is None:
            self._server_name = server_name
        else:
            raise ValueError('Server contains invalid characters')
        self._set_owner(owner, group)
        self._create_logger()
        self._set_environment()
        self._load_config()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def _set_owner(self,
                   owner,
                   group,
                   base_directory='',
                   container_directory=''):
        """
        Sets the instance to be executed by linux user 'owner'.
        Sets self._homepath from linux-provided HOMEDIR,
        effectively containing new directory creation.

        """
        from pwd import getpwnam
        from grp import getgrnam, getgrgid


        if owner is None:
            from getpass import getuser
            owner = getuser()
        elif type(owner) is not str:
            raise TypeError('Supplied argument "owner" must be string')
        else:
            getpwnam(owner)

        if group is None:
            try:
                group = getgrgid(getpwnam(owner).pw_gid).gr_name
            except KeyError:
                raise KeyError('Supplied owner does not exist %s' % owner)
        elif type(group) is not str:
            raise TypeError('Supplied argument "group" must be string')
        else:
            getgrnam(group)

        if owner in getgrnam(group).gr_mem:
            self._group = getgrnam(group)
            self._owner = getpwnam(owner)
        else:
            raise OSError('%s is not part of group %s' % (owner, group))
            
        if base_directory:
            self._homepath = os.path.join(base_directory, container_directory)
        else:
            self._homepath = os.path.join(self._owner.pw_dir, container_directory)
            
        '''
        self._homepath will typically go to /home/user,
        but this can be modified by supplying base_directory, such as:
        base_directory = '/var/games/minecraft'
        container_directory = 'mineos'

        resulting structure ==> /var/games/minecraft/mineos/{servers,backup,archive}

        Supplying base_directory will likely require root/chown-ing base_directory.

        FIXME: this functionality is not yet usable, as __init__ does not provide
        base_directory or container_directory to this method.
        '''
        for p in self.DEFAULT_PATHS.values():
            self._make_directory(os.path.join(self._homepath, p))

    def _set_environment(self):
        """
        Sets the most common short-hand paths for the minecraft directories
        and configuration files.

        """
        if not self.server_name:
            return

        self.server_properties = None
        self.server_config = None
        
        self.env = {}

        self.env['cwd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['servers'], self.server_name)
        self.env['bwd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['backup'], self.server_name)
        self.env['awd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['archive'], self.server_name)
        self.env['lwd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['log'], self.server_name)
        self.env['pwd'] = os.path.join(self._homepath, self.DEFAULT_PATHS['profiles'])
        self.env['pc'] = os.path.join(self._homepath, self.DEFAULT_PATHS['profiles'], 'profile.config')
        self.env['sp'] = os.path.join(self.env['cwd'], 'server.properties')
        self.env['sc'] = os.path.join(self.env['cwd'], 'server.config')
        self.env['sp_backup'] = os.path.join(self.env['bwd'], 'server.properties')
        self.env['sc_backup'] = os.path.join(self.env['bwd'], 'server.config')

    def _load_config(self, load_backup=False, generate_missing=False):
        """
        Loads server.properties and server.config for a given server.
        With load_backup, /backup/ is referred to rather than /servers/.
        generate_missing will create one and only one missing configuration
        with hard-coded defaults. generate_missing currently should
        only be utilized as a fallback when starting a server.

        FUTURE: create a method that detects missing config files and
        fills in user-approved values (even if default).        

        """
        def load_sp():
            self.server_properties = config_file(self.env['sp_backup']) if load_backup else config_file(self.env['sp'])
            return self.server_properties[:]

        def load_sc():
            self.server_config = config_file(self.env['sc_backup']) if load_backup else config_file(self.env['sc'])
            return self.server_config[:]

        def load_profiles():
            self.profile_config = config_file(self.env['pc'])
            return self.profile_config[:]

        if hasattr(self, 'env'):
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

        for section, option in sanitize_integers:
            try:
                defaults[section][option] = int(startup_values[section][option])
            except (KeyError, ValueError):
                continue
                
        with config_file(self.env['sc']) as sc:
            for section in defaults:
                sc.add_section(section)
                for option in defaults[section]:
                    sc[section:option] = str(defaults[section][option])

    def create(self, sc={}, sp={}):
        """
        Creates a server's directories and generates configurations.

        """
        if self.server_name in self.list_servers():
            raise RuntimeWarning('Ignoring command {create}; server already exists.')

        for d in ('cwd', 'bwd', 'awd'):
            self._make_directory(self.env[d])

        sc = sc if type(sc) is dict else {}
        sp = sp if type(sp) is dict else {}
        self._create_sc(sc)
        self._create_sp(sp)
        self._load_config()
    
    def start(self):
        """
        Checks if a server is running on its bound IP:PORT
        and if not, starts the screen+java instances.

        """
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {start}; no server by this name.')
        elif self.up:
            raise RuntimeWarning('Ignoring command {start}; server already up at %s:%s.' % (self.ip_address, self.port))
        
        if self.port in [s.port for s in self.list_ports_up()]:
            if (self.port, self.ip_address) in [(s.port, s.ip_address) for s in self.list_ports_up()]:
                raise RuntimeError('Ignoring command {start}; server already up at %s:%s.' % (self.ip_address, self.port))
            elif self.ip_address == '0.0.0.0':
                raise RuntimeError('Ignoring command {start}; can not listen on (0.0.0.0) if port %s already in use.' % self.port)
            elif any(s for s in self.list_ports_up() if s.ip_address == '0.0.0.0'):
                raise RuntimeError('Ignoring command {start}; server already listening on ip address (0.0.0.0).')

        self._load_config(generate_missing=True)
        self._logger.info('Executing command {start}; %s@%s:%s', self.server_name, self.ip_address, self.port)

        self._command_direct(self.command_start, self.env['cwd'])

    def kill(self):
        """
        Kills a server instance by SIGTERM

        """
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {kill}; no server by this name.')
        elif self.up:
            from signal import SIGTERM
            self._logger.info('Executing command {kill}: %s', self.server_name)
            os.kill(self.java_pid, SIGTERM)
        else:
            raise RuntimeWarning('Ignoring command {kill}: no live process for server %s' % self.server_name)

    def archive(self):
        """
        Creates a timestamped, gzipped tarball of the server contents.

        """
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {start}; no server by this name.')
        elif self.up:
            self._logger.info('Executing command {archive}: %s', command)
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_archive, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_archive, self.env['cwd'])

    def backup(self):
        """
        Creates an rdiff-backup of a server.

        """
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {start}; no server by this name.')
        elif self.up:
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_backup, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_backup, self.env['cwd'])

    def restore(self, steps='now', overwrite=False):
        """
        Overwrites the /servers/ version of a server with the /backup/.

        """
        from subprocess import CalledProcessError
        
        if self.server_name not in self.list_servers():
            raise RuntimeWarning('Ignoring command {restore}; no server by this name.')
        elif self.up:
            raise RuntimeError('Ignoring command {restore}; server %s currently up' % self.server_name)
        
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

    def prune(self, steps=None):
        """
        Removes old rdiff-backup data/metadata.

        FIXME: Does not do any sanitization on steps.

        """
        self._rdiff_backup_steps = steps
        self._command_direct(self.command_prune, self.env['bwd'])

    def update_profile(self, profile_dict, do_download=True):

        self._make_directory(os.path.join(self.env['pwd'],
                                          profile_dict['name']))

        with self.profile_config as pc:
            from ConfigParser import DuplicateSectionError
            
            try:
                pc.add_section(profile_dict['name'])
            except DuplicateSectionError:
                pass
            
            for option, value in profile_dict.iteritems():
                if option != 'name':
                    pc[profile_dict['name']:option] = value

        if profile_dict['type'] == 'standard_jar':
            from shutil import move

            if profile_dict['action'] == 'download' and do_download:
                self._update_file(profile_dict['url'],
                                  self.env['pwd'],
                                  profile_dict['save_as'])
            
                move(os.path.join(self.env['pwd'],
                                  pc[profile_dict['name']:'save_as']),
                     os.path.join(self.env['pwd'],
                                  profile_dict['name'],
                                  pc[profile_dict['name']:'run_as']))
        else:
            raise NotImplementedError

    def _demote(self, user_uid, user_gid):
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

        self._logger.info('Executing as %s from %s: %s', self._owner.pw_name,
                                                         working_directory,
                                                         command)

        return check_output(command,
                            shell=True,
                            cwd=working_directory,
                            stderr=STDOUT,
                            preexec_fn=self._demote(self._owner.pw_uid,
                                                    self._group.gr_gid))

    def _command_stuff(self, stuff_text):
        """
        Opens a subprocess and stuffs text to an open screen as the user
        specified in self._owner.

        """
        from subprocess import check_call

        if self.up:
            command = """screen -S %d -p 0 -X eval 'stuff "%s\012"'""" % (self.screen_pid, stuff_text)
            self._logger.info('Executing as %s: %s', self._owner.pw_name,
                                                     command)

            check_call(command,
                       shell=True,
                       preexec_fn=self._demote(self._owner.pw_uid,
                                               self._group.gr_gid))
        else:
            self._logger.warning('Ignoring command {stuff}; downed server %s: "%s"', self.server_name, stuff_text)
            raise RuntimeError('Server must be running to send screen commands')

    def _create_logger(self):
        """
        Create a logger item.

        """
        self._make_directory(os.path.join(self._homepath, self.DEFAULT_PATHS['log']))

        if not self.server_name:
            return
        
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
        """
        Closes the self._logger filehandler (is not implemented anywhere).

        """
        if self._logger_fh:
            self._logger_fh.close()

    def valid_server_name(self, name):
        """
        Checks if a server name is only alphanumerics,
        underscores or dots.

        """
        valid_chars = set('%s%s_.' % (ascii_letters, digits))

        if not name:
            return False
        if any(c for c in name if c not in valid_chars):
            return False
        elif name.startswith('.'):
            return False
        return True

    ''' properties '''

    @property
    def server_name(self):
        """
        Returns the name of the server.

        """
        return self._server_name

    @property
    def up(self):
        """
        Returns True if the server has a running process.

        """
        return self.server_name in self.list_servers_up()

    @property
    def java_pid(self):
        """
        Returns the process id of the server's java instance.

        """
        for server, java_pid, screen_pid in self._list_server_pids():
            if self.server_name == server:
                return java_pid
        else:
            return 0

    @property
    def screen_pid(self):
        """
        Returns the process id of the server's screen instance.

        """
        for server, java_pid, screen_pid in self._list_server_pids():
            if self.server_name == server:
                return screen_pid
        else:
            return 0

    @property
    def previous_arguments(self):
        try:
            return self._previous_arguments
        except AttributeError:
            return None
    
    @property
    def command_start(self):
        """
        Returns the actual command used to start up a minecraft server.

        FIXME: this does not currently implement profiles and depends
        on the server jar being called 'minecraft_server.jar'.

        This is a placeholder until it is decided whether profiles will
        be using symlinks to /jars/[somefile.jar] or if they will
        remain at the root.

        """
        if not self.server_config:
            return None

        required_arguments = {
            'screen_name': 'mc-%s' % self.server_name,
            'screen': self.BINARY_PATHS['screen'],
            'java': self.BINARY_PATHS['java'],
            'java_xmx': self.server_config['java':'java_xmx'],
            'java_xms': self.server_config['java':'java_xmx'],
            'java_tweaks': self.server_config['java':'java_tweaks'],
            'jar_file': os.path.join(self.env['cwd'], 'minecraft_server.jar'),
            'jar_args': '-nogui'
            }

        if self.server_config.has_option('java','java_xms') :
            required_arguments['java_xms'] = self.server_config['java':'java_xms']

        if None in required_arguments.values():
            raise RuntimeError('Missing value in start command: %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(screen)s -dmS %(screen_name)s ' \
                   '%(java)s %(java_tweaks)s -Xmx%(java_xmx)sM -Xms%(java_xms)sM ' \
                   '-jar %(jar_file)s %(jar_args)s' % required_arguments

    @property
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


        if None in required_arguments.values():
            raise RuntimeError('Missing value in archive command: %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(nice)s -n %(nice_value)s ' \
                   '%(tar)s czf %(archive_filename)s %(cwd)s' % required_arguments

    @property
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

        if None in required_arguments.values():
            raise RuntimeError('Missing value in backup command: %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(nice)s -n %(nice_value)s ' \
                   '%(rdiff)s %(cwd)s/ %(bwd)s' % required_arguments

    @property
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

        if None in required_arguments.values():
            raise RuntimeError('Missing value in restore command: %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(rdiff)s %(force)s --restore-as-of %(steps)s ' \
                   '%(bwd)s %(cwd)s' % required_arguments

    @property
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

        if None in required_arguments.values():
            raise RuntimeError('Missing value in prune command: %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(rdiff)s --force --remove-older-than %(steps)s %(bwd)s' % required_arguments

    @property
    def command_list_increments(self):
        """
        Returns the number of increments found at the backup dir

        """
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'bwd': self.env['bwd']
            }

        if None in required_arguments.values():
            raise RuntimeError('Missing value in list_increments command; %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(rdiff)s --list-increments %(bwd)s' % required_arguments

    @property
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

        if None in required_arguments.values():
            raise RuntimeError('Missing value in apply_profile command: %s' % str(required_arguments))
        else:
            self._previous_arguments = required_arguments
            return '%(rsync)s -a %(exclude)s %(pwd)s/%(profile)s/ %(cwd)s' % required_arguments

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
                
        try:
            mem_str = dict(procfs_reader.entries(self.java_pid, 'status'))['VmRSS']
            mem = int(mem_str.split()[0]) * 1024
            return sizeof_fmt(mem)
        except IOError:
            return '0'

    ''' generator expressions '''

    def list_servers(self):
        """
        Lists all directories in /servers/ and /backup/.
        Note, not all listings may be servers.

        """
        from itertools import chain
        return set(chain(
            self._list_subdirs(os.path.join(self._homepath, self.DEFAULT_PATHS['servers'])),
            self._list_subdirs(os.path.join(self._homepath, self.DEFAULT_PATHS['backup']))
            ))

    def list_servers_up(self):
        """
        Generator: all servers which were started with "mc-SERVER" name.

        """
        for instance in set(self._list_server_pids()):
            yield instance.server_name

    def list_ports_up(self):
        """
        Returns IP address and port used by all live,
        running instances of Minecraft.

        """
        instance_connection = namedtuple('instance_connection', 'server_name port ip_address')
        for server in self.list_servers_up():
            instance = mc(server)
            yield instance_connection(server, instance.port, instance.ip_address)

    def list_increments(self):
        """
        Returns a tuple of the timestamp of the most current mirror
        and a list of all the increment files found.

        """
        from subprocess import CalledProcessError

        incs = namedtuple('increments', 'current_mirror increments')
        
        try:
            output = self._command_direct(self.command_list_increments, self.env['bwd'])
        except CalledProcessError:
            return incs('', [])
            
        output_list = output.split('\n')
        increment_string = output_list.pop(0)
        output_list.pop() #empty newline throwaway
        current_string = output_list.pop()

        '''num_increments = iter(int(p) for p in increment_string.split() if p.isdigit()).next()'''
        timestamp = current_string.partition(':')[-1].strip()
        
        return incs(timestamp, [d.strip() for d in output_list])
            
    def _list_subdirs(self, directory):
        """
        Returns a list of all subdirectories of a path.

        """
        try:
            return os.walk(directory).next()[1]
        except StopIteration:
            return []

    def _list_files(self, directory):
        """
        Returns a list of all files in a path (no recursion).

        """
        try:
            return os.walk(directory).next()[2]
        except StopIteration:
            return []

    def _list_server_pids(self):
        """
        Generator: screen and java pid info for all running servers
        Returns: (server_name, java_pid, screen_pid)
        
        """
        import re

        instance_pids = namedtuple('instance_pids', 'server_name java_pid screen_pid')
        pids = set(procfs_reader.pid_cmdline())
        servers = []
        retval = {}
        
        for pid, cmdline in pids:
            if 'screen' in cmdline.lower():
                serv = re.search(r'SCREEN.*?mc-([\w._]+)', cmdline, re.IGNORECASE)
                try:
                    servers.append(serv.groups()[0])
                except AttributeError:
                    pass

        for serv in servers:
            java = None
            screen = None
            for pid, cmdline in pids:
                if '-jar' in cmdline:
                    if 'screen ' in cmdline.lower() and 'mc-%s ' % serv in cmdline:
                        screen = int(pid)
                    elif '/%s/' % serv in cmdline:
                        java = int(pid)
                if java and screen:
                    break
            yield instance_pids(serv, java, screen)

# chowning functions

    def _make_directory(self, path, do_raise=False):
        """
        Creates a directory and chowns it to self._owner.
        Fails silently.

        """
        try:
            os.makedirs(path)
        except OSError:
            if do_raise:
                raise
        else:
            os.chown(path,
                     self._owner.pw_uid,
                     self._owner.pw_gid)

    def _update_file(self, url, root_path, dest_filename):
        """
        Downloads a file and checks md5sum hash versus any existing file.
        Keyword arguments:
        url -- url of resource
        root_path -- base directory where file should be saved
        dest_filename -- ultimate filename of downloaded resource
        
        Returns:
        True: if download is successful and retained
        False: if download is successful and discarded
        
        Raises:
        IOError: internet non-connectivity or overwrite failure
        
        """
        from urllib import FancyURLopener
        
        def md5sum(filepath):
            from hashlib import md5
            with open(filepath, 'rb') as infile:
                m = md5()
                m.update(infile.read())
                return m.hexdigest()

        self._make_directory(root_path)
        old_path = os.path.join(root_path, dest_filename)
        try:
            old_md5 = md5sum(old_path)
        except IOError:
            old_md5 = None #dest_file does not exist to md5

        new_path = os.path.join(root_path, '%s.new' % dest_filename)

        try:
            FancyURLopener().retrieve(url, new_path)
        except IOError:
            raise IOError('Invalid download URL or no internet connection, aborting download...')
        else:
            new_md5 = md5sum(new_path)

        if new_md5 != old_md5:
            from shutil import move
            try:
                os.chown(new_path,
                         self._owner.pw_uid,
                         self._owner.pw_gid)
                move(new_path, old_path)
            except IOError:
                raise IOError('move() activity failed')
            else:
                #Existing file overwritten with new copy
                return True
        else:
            try:
                os.unlink(new_path)
            except IOError:
                raise IOError('unlink() activity failed')
            else:
                return False

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
                             self._owner.pw_uid,
                             self._owner.pw_gid)
            except (IOError, os.error) as why:
                errors.append((srcname, dstname, str(why)))
            except Error as err:
                errors.extend(err.args[0])
        try:
            copystat(src, dst)
        except OSError as why:
            errors.extend((src, dst, str(why)))

