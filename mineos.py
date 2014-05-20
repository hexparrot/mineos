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
    """Checks that attempted CLI commands have all required fields.

    Raises RuntimeError if false.
    """
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        return_func = fn(self, *args, **kwargs)
        if None in self.previous_arguments.values():
            raise RuntimeError('Missing value in %s: %s' % (fn.__name__,str(self.previous_arguments)))
        return return_func
    return wrapper

def server_exists(state):
    """Decorator to ensure that the command being executed
    has a created working directory.

    Accepts: True/False

    Raises RuntimeWarning if expected value != actual value.
    """
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
    """Decorator to ensure attempted command is currently running

    Accepts: True/False

    Raises RuntimeError if expected state != actual state
    """
    def dec(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self.up == up:
                fn(self, *args, **kwargs)
            else:
                if up:
                    raise RuntimeError('Server must be running to perform this action.')
                else:
                    raise RuntimeError('Server may not be running when performing this action.')
        return wrapper
    return dec

class mc(object):

    NICE_VALUE = 10
    DEFAULT_PATHS = {
        'servers': 'servers',
        'backup': 'backup',
        'archive': 'archive',
        'profiles': 'profiles',
        'import': 'import'
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
    LOG_PATHS = {
        'legacy': 'server.log',
        'current': os.path.join('logs', 'latest.log'),
        'bungee': 'proxy.log.0',
        'forgemod': 'ForgeModLoader-server-0.log'
        } 
    
    def __init__(self,
                 server_name,
                 owner=None,
                 base_directory=None):
        from getpass import getuser

        self._server_name = self.valid_server_name(server_name)
        self._owner = owner or getuser()
        self._base_directory = base_directory or os.path.expanduser("~")

        self._set_environment()
        try:
            self._load_config(generate_missing=True)
        except RuntimeError:
            pass
        else:
            if self.server_config.has_option('java', 'java_bin'):
                self.upgrade_old_config()

    def _set_environment(self):
        """Sets the most common short-hand paths for the minecraft directories
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

        for server_type, lp in sorted(self.LOG_PATHS.iteritems()):
            #implementation detail; sorted() depends on 'current' always preceeding 'legacy',
            #to ensure that current is always tested first in the event both logfiles exist.
            path = os.path.join(self.env['cwd'], lp)
            if os.path.isfile(path):
                self.env['log'] = path
                self._server_type = server_type
                break
        else:
            self._server_type = 'unknown'

    def _load_config(self, load_backup=False, generate_missing=False):
        """Loads server.properties and server.config for a given server.
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

    def upgrade_old_config(self):
        """Checks server.config for obsolete attributes from previous versions"""
        def extract():
            """Extracts relevant attributes from old config"""
            from ConfigParser import NoOptionError, NoSectionError
            from collections import defaultdict

            new_config = defaultdict(dict)
            kept_attributes = {
                'onreboot': ['restore', 'start'],
                'java': ['java_tweaks', 'java_xmx', 'java_xms']
                }

            for section in kept_attributes:
                for option in kept_attributes[section]:
                    try:
                        new_config[section][option] = self.server_config[section:option]
                    except (KeyError, NoOptionError, NoSectionError):
                        pass
            return dict(new_config)
    
        self._command_direct('rm -- %s' % self.env['sc'], self.env['cwd'])
        self._create_sc(extract())
        self._load_config()

    @server_exists(True)
    def _create_sp(self, startup_values={}):
        """Creates a server.properties file for the server given a dict.
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
        """Creates a server.config file for a server given a dict.
        
        Expected startup_values should match format of "defaults".
        """
        defaults = {
            'minecraft': {
                'profile': '',
                },
            'crontabs': {
                'archive_interval': '',
                'backup_interval': '',
                'restart_interval': '',
                },
            'onreboot': {
                'restore': False,
                'start': False,
                },
            'java': {
                'java_tweaks': '',
                'java_xmx': 256,
                'java_xms': 256,
                'java_debug': False
                }
            }

        sanitize_integers = set([('java', 'java_xmx'),
                                 ('java', 'java_xms'),
                                 ('crontabs', 'archive_interval'),
                                 ('crontabs', 'backup_interval'),
                                 ('crontabs', 'restart_interval')
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
        """Creates a server's directories and generates configurations."""
        for d in ('cwd', 'bwd', 'awd'):
            self._make_directory(self.env[d], True)

        sc = sc if type(sc) is dict else {}
        sp = sp if type(sp) is dict else {}
        self._create_sc(sc)
        self._create_sp(sp)
        self._load_config()

    @server_exists(True)
    def modify_config(self, option, value, section=None):
        """Modifies a value in server.properties or server.config"""
        if section:
            with self.server_config as sc:
                sc[section:option] = value
        else:
            with self.server_properties as sp:
                sp[option] = value

    def modify_profile(self, option, value, section):
        """Modifies a value in profile.config
        Whitelisted values that can be changed.
        """
        if option in ['desc']:
            with self.profile_config as pc:
                pc[section:option] = value

    @server_exists(True)
    @server_up(False)
    def start(self):
        """Checks if a server is running on its bound IP:PORT
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
        if not self.profile_current:
            self.profile = self.profile

        self._command_direct(self.command_start, self.env['cwd'])

    @server_exists(True)
    @server_up(True)
    def kill(self):
        """Kills a server instance by SIGTERM"""
        self._command_direct(self.command_kill, self.env['cwd'])

    @server_exists(True)
    @server_up(True)
    def commit(self):
        """Commit a server's memory to disk"""
        self._command_stuff('save-all')

    @server_exists(True)
    @server_up(True)
    def stop(self):
        """Stop a server"""
        if self.server_type == 'bungee':
            self._command_stuff('end')
        else:
            self._command_stuff('stop')

    @server_exists(True)
    def archive(self):
        """Creates a timestamped, gzipped tarball of the server contents."""
        self._make_directory(self.env['awd'])
        if self.up:
            self._command_stuff('save-off')
            try:
                self._command_direct(self.command_archive, self.env['cwd'])
            finally:
                self._command_stuff('save-on')
        else:
            self._command_direct(self.command_archive, self.env['cwd'])

    @server_exists(True)
    def backup(self):
        """Creates an rdiff-backup of a server."""
        self._make_directory(self.env['bwd'])
        if self.up:
            self._command_stuff('save-off')
            self._command_stuff('save-all')
            self._command_direct(self.command_backup, self.env['cwd'])
            self._command_stuff('save-on')
        else:
            self._command_direct(self.command_backup, self.env['cwd'])

    @server_exists(True)
    @server_up(False)
    def restore(self, step='now', force=False):
        """Overwrites the /servers/ version of a server with the /backup/."""
        from subprocess import CalledProcessError
        
        self._load_config(load_backup=True)

        if self.server_properties or self.server_config:
            force = '--force' if force else ''

            self._make_directory(self.env['cwd'])
            try:
                self._command_direct(self.command_restore(step,force), self.env['cwd'])
            except CalledProcessError as e:
                raise RuntimeError(e.output)

            self._load_config(generate_missing=True)
        else:
            raise RuntimeError('Ignoring command {restore}; Unable to locate backup')

    @server_exists(False)
    def import_server(self, path, filename):
        """ Extracts an existing archive into the live space.
        Might need additional review if run as root by server.py
        """
        import tarfile, zipfile
        
        filepath = os.path.join(path, filename)

        if tarfile.is_tarfile(filepath):
            archive_ = tarfile.open(filepath, mode='r')
            members_ = archive_.getnames()
            prefix_ = os.path.commonprefix(members_)
        elif zipfile.is_zipfile(filepath):
            archive_ = zipfile.ZipFile(filepath, 'r')
            members_ = archive_.namelist()
            prefix_ = os.path.commonprefix(members_)
        else:
            raise NotImplementedError('Ignoring command {import_server};'
                                      'archive file must be compressed tar or zip')

        if any(f for f in members_ if f.startswith('/') or '..' in f):
            raise RuntimeError('Ignoring command {import_server};'
                               'archive contains files with absolute path or ..')
        
        archive_.extractall(self.env['cwd'])

        if not os.path.samefile(self.env['cwd'], os.path.join(self.env['cwd'], prefix_)):     
            prefixed_dir = os.path.join(self.env['cwd'], prefix_)

            from distutils.dir_util import copy_tree
            copy_tree(prefixed_dir, self.env['cwd'])

            from shutil import rmtree
            rmtree(prefixed_dir)
        
        self._load_config(generate_missing=True)

    @server_exists(True)
    def prune(self, step):
        """Removes old rdiff-backup data/metadata."""
        self._command_direct(self.command_prune(step), self.env['bwd'])

    def prune_archives(self, filename):
        """Removes old archives by filename as a space-separated string."""
        self._command_direct(self.command_delete_files(filename), self.env['awd'])

    @server_exists(True)
    @server_up(False)
    def delete_server(self):
        """Deletes server files from system"""
        self._command_direct(self.command_delete_server, self.env['pwd'])

    def remove_profile(self, profile):
        """Removes a profile found in profile.config at the base_directory root"""
        try:
            if self.has_ownership(self._owner, self.env['pc']):
                from shutil import rmtree
                rmtree(os.path.join(self.env['pwd'], profile))

                with self.profile_config as pc:
                    pc.remove_section(profile)
        except OSError as e:
            from errno import ENOENT
            if e.errno == ENOENT:
                with self.profile_config as pc:
                    pc.remove_section(profile)
            else:
                raise RuntimeError('Ignoring command {remove_profile}; User does not have permissions on this profile')
            
    def define_profile(self, profile_dict):
        """Accepts a dictionary defining how to download and run a piece
        of Minecraft server software.

        profile_dict = {
            'name': 'vanilla',
            'type': 'standard_jar',
            'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
            'save_as': 'minecraft_server.jar',
            'run_as': 'minecraft_server.jar',
            'ignore': '',
            }

        """

        profile_dict['run_as'] = self.valid_filename(os.path.basename(profile_dict['run_as']))
        
        if profile_dict['type'] == 'unmanaged':
            for i in ['save_as', 'url', 'ignore']:
                profile_dict[i] = ''
        else:
            profile_dict['save_as'] = self.valid_filename(os.path.basename(profile_dict['save_as']))

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
        """Download's a profile via the provided URL.
        If expected_md5 is provided, it can either:
        1) reject downloads not matching expected md5
        2) avoid unnecessary download if existing md5 == expected md5
        """
        self._make_directory(os.path.join(self.env['pwd'], profile))
        profile_dict = self.profile_config[profile:]

        if profile_dict['type'] == 'unmanaged':
            raise RuntimeWarning('No action taken; unmanaged profile')
        elif profile_dict['type'] in ['archived_jar', 'standard_jar']:
            with self.profile_config as pc:
                pc[profile:'save_as'] = self.valid_filename(os.path.basename(pc[profile:'save_as']))
                pc[profile:'run_as'] = self.valid_filename(os.path.basename(pc[profile:'run_as']))

            old_file_path = os.path.join(self.env['pwd'], profile, profile_dict['save_as'])

            try:
                old_file_md5 = self._md5sum(old_file_path)
            except IOError:
                old_file_md5 = None
            finally:
                if expected_md5 and old_file_md5 == expected_md5:
                    raise RuntimeWarning('Did not download; expected md5 == existing md5')

            new_file_path = os.path.join(self.env['pwd'], profile, profile_dict['save_as'] + '.new')

            from subprocess import CalledProcessError
            try:
                self._command_direct(self.command_wget_profile(profile),
                                     os.path.join(self.env['pwd'], profile))
            except CalledProcessError:
                self._command_direct(self.command_wget_profile(profile, True),
                                     os.path.join(self.env['pwd'], profile))

            new_file_md5 = self._md5sum(new_file_path)

            if expected_md5 and expected_md5 != new_file_md5:
                raise RuntimeError('Discarding download; expected md5 != actual md5')
            elif old_file_md5 == new_file_md5:
                os.unlink(new_file_path)
                raise RuntimeWarning('Discarding download; new md5 == existing md5')
            '''elif self.profile_config[profile:'save_as_md5'] == new_file_md5:
                potentially removable.
                os.unlink(new_file_path)
                raise RuntimeWarning('Discarding download; new md5 == existing md5')'''

            if profile_dict['type'] == 'archived_jar':
                import zipfile, tarfile
                if zipfile.is_zipfile(new_file_path):
                    with zipfile.ZipFile(new_file_path, mode='r') as zipchive:
                        zipchive.extractall(os.path.join(self.env['pwd'], profile))
                elif tarfile.is_tarfile(new_file_path):
                    with tarfile.open(new_file_path, mode='r') as tarchive:
                        tarchive.extractall(os.path.join(self.env['pwd'], profile))

                new_run_as = os.path.join(os.path.join(self.env['pwd'], profile, profile_dict['run_as']))
                with self.profile_config as pc:
                    pc[profile:'save_as_md5'] = new_file_md5
                    pc[profile:'run_as_md5'] = self._md5sum(new_run_as)

                os.unlink(new_file_path)
                return new_file_md5
            elif profile_dict['type'] == 'standard_jar':
                from shutil import move

                move(new_file_path, old_file_path)
                active_md5 = self._md5sum(old_file_path)

                with self.profile_config as pc:
                    pc[profile:'save_as_md5'] = active_md5
                    pc[profile:'run_as_md5'] = active_md5
                
                return self._md5sum(old_file_path)
        else:
            raise NotImplementedError("This type of profile is not implemented yet.")

    @staticmethod
    def server_version(filepath, guess=''):
        """Extract server version from jarfile and fallback
        to guessing by URL"""
        import zipfile
        from xml.dom.minidom import parseString

        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                files = zf.namelist()
                for internal_path in [r'META-INF/maven/org.bukkit/craftbukkit/pom.xml',
                                      r'META-INF/maven/mcpc/mcpc-plus-legacy/pom.xml',
                                      r'META-INF/maven/mcpc/mcpc-plus/pom.xml',
                                      r'META-INF/maven/org.spigotmc/spigot/pom.xml',
                                      r'META-INF/maven/net.md-5/bungeecord-api/pom.xml']:
                    if internal_path in files:
                        for tag in ['minecraft.version', 'version']:
                            try:
                                xml = parseString(zf.read(internal_path))
                                return xml.getElementsByTagName(tag)[0].firstChild.nodeValue
                            except (IndexError, KeyError, AttributeError):
                                continue 
        except IOError:
            return ''
        else:
            import re
            match = re.match('https://s3.amazonaws.com/Minecraft.Download/versions/([^/]+)', guess)
            try:
                return match.group(1)
            except AttributeError:
                return ''

#actual command execution methods

    @staticmethod
    def _demote(user_uid, user_gid):
        """Closure for _command_direct and _command_stuff that changes
        current user to that of self._owner.pd_{uid,gid}

        Usually this will demote, when this script is running as root,
        otherwise it will set its gid and uid to itself.
        """
        def set_ids():
            os.umask(2)
            os.setgid(user_gid)
            os.setuid(user_uid)
        return set_ids

    def _command_direct(self, command, working_directory):
        """Opens a subprocess and executes a command as the user
        specified in self._owner.
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
        """Opens a subprocess and stuffs text to an open screen as the user
        specified in self._owner.
        """
        from subprocess import check_call
        from shlex import split

        command = """%s -S %d -p 0 -X eval 'stuff "%s\012"'""" % (self.BINARY_PATHS['screen'],
                                                                  self.screen_pid,
                                                                  stuff_text)
        check_call(split(command),
                   preexec_fn=self._demote(self.owner.pw_uid, self.owner.pw_gid))

#validation checks

    @staticmethod
    def valid_server_name(name):
        """Checks if a server name is only alphanumerics, underscores or dots."""
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
    def valid_filename(filename):
        """Checks filename against whitelist-safe characters"""
        from string import ascii_letters, digits
        
        valid_chars = set('%s%s-_.' % (ascii_letters, digits))

        if not filename:
            raise ValueError('Filename is empty')
        elif any(c for c in filename if c not in valid_chars):
            raise ValueError('Disallowed characters in filename "%s"' % filename)
        elif filename.startswith('.'):
            raise ValueError('Files should not be hidden: "%s"' % filename)
        return filename

    ''' properties '''

    @property
    def server_name(self):
        """Returns the name of the server."""
        return self._server_name

    @property
    def base(self):
        """Returns the root path of the server."""
        return self._base_directory

    @property
    def owner(self):
        """Returns pwd named tuple"""
        from pwd import getpwnam
        return getpwnam(self._owner)

    @property
    def up(self):
        """Returns True if the server has a running process."""
        return any(s.server_name == self.server_name for s in self.list_servers_up())

    @property
    def java_pid(self):
        """Returns the process id of the server's java instance."""
        for server, java_pid, screen_pid, base_dir in self.list_servers_up():
            if self.server_name == server:
                return java_pid
        else:
            return None

    @property
    def screen_pid(self):
        """Returns the process id of the server's screen instance."""
        for server, java_pid, screen_pid, base_dir in self.list_servers_up():
            if self.server_name == server:
                return screen_pid
        else:
            return None

    @property
    def profile(self):
        """Returns the profile the server is set to"""
        try:
            return self.server_config['minecraft':'profile'] or None
        except KeyError:
            return None

    @profile.setter
    def profile(self, profile):
        """Sets a profile for a server, checking that the profile
        exists as an entry in 'profile.config'"""
        try:
            self.profile_config[profile:]
        except KeyError:
            raise KeyError('There is no defined profile "%s" in profile.config' % profile)
        else:
            with self.server_config as sc:
                from ConfigParser import DuplicateSectionError
                
                try:
                    sc.add_section('minecraft')
                except DuplicateSectionError:
                    pass
                finally:
                    sc['minecraft':'profile'] = str(profile).strip()

            self._command_direct(self.command_apply_profile(profile), self.env['cwd'])

    @property
    def profile_current(self):
        """Checks that the expected md5 of a server jar matches the one
        in the LIVE SERVER DIRECTORY (e.g., update newer than executed)
        """
        def compare(profile):
            return self._md5sum(os.path.join(self.env['pwd'],
                                             profile,
                                             self.profile_config[current:'run_as'])) == \
                   self._md5sum(os.path.join(self.env['cwd'],
                                             self.profile_config[current:'run_as']))
        
        try:
            current = self.profile
            if self.profile_config[current:'type'] == 'unmanaged':
                path_ = os.path.join(self.env['cwd'], self.profile_config[current:'run_as'])
                if not os.path.isfile(path_):
                    raise RuntimeError('%s does not exist' % path_)
                else:
                    return True
            return compare(current)
        except TypeError:
            raise RuntimeError('Server is not assigned a valid profile.')
        except IOError as e:
            from errno import ENOENT
            if e.errno == ENOENT:
                self.profile = current
            return compare(current)

    @property
    def port(self):
        """Returns the port value from server.properties at time of instance creation."""
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
        """Returns the ip address value from server.properties at time of instance creation.
        This may return '0.0.0.0' even if that is not the value in the file,
        because it is the effective value vanilla minecraft will run at.
        """
        return self.server_properties['server-ip'::'0.0.0.0'] or '0.0.0.0'
        ''' If server-ip is absent, vanilla starts at *,
            which is effectively 0.0.0.0 and
            also adds 'server-ip=' to server.properties.'''

    @property
    def memory(self):
        """Returns the amount of memory the java instance is using (VmRSS)"""
        def bytesto(num, to, bsize=1024):
            """convert bytes to megabytes, etc.
               sample code:
                   print('mb= ' + str(bytesto(314575262000000, 'm')))

               sample output: 
                   mb= 300002347.946
               https://gist.github.com/shawnbutts/3906915
            """
            a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6 }
            r = float(num)
            for i in range(a[to]):
                r = r / bsize

            return r

        from procfs_reader import entries

        try:
            mem_str = dict(entries(self.java_pid, 'status'))['VmRSS']
            mem = int(mem_str.split()[0]) * 1024
            return '%s MB' % bytesto(mem, 'm')
        except IOError:
            return '0'

    @property
    def ping(self):
        """Returns a named tuple using the current Minecraft protocol
        to retreive versions, player counts, etc"""
        import socket

        def server_list_packet():
            """Guesses what version minecraft a live server directory is."""
            if self.server_milestone_short in ['1.5', '1.6'] or \
               (self.server_type == 'forgemod' and self.server_milestone == 'unknown'):
                return '\xfe' \
                       '\x01' \
                       '\xfa' \
                       '\x00\x06' \
                       '\x00\x6d\x00\x69\x00\x6e\x00\x65\x00\x6f\x00\x73' \
                       '\x00\x19' \
                       '\x49' \
                       '\x00\x09' \
                       '\x00\x6c\x00\x6f\x00\x63\x00\x61\x00\x6c\x00\x68' \
                       '\x00\x6f\x00\x73\x00\x74' \
                       '\x00\x00\x63\xdd'
            else:
                return '\xfe\x01'

        server_ping = namedtuple('ping', ['protocol_version',
                                          'server_version',
                                          'motd',
                                          'players_online',
                                          'max_players'])

        error_ping = server_ping(None,None,self.server_properties['motd'::''],
                                 '-1',self.server_properties['max-players'])

        if self.server_type == 'bungee':
            return server_ping(None,None,'','0',1)
        elif self.up:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.ip_address, self.port))
                s.send(server_list_packet())

                d = s.recv(1024)
                s.shutdown(socket.SHUT_RDWR)
            except socket.error:
                return error_ping
            finally:
                s.close()

            if d[0] == '\xff':
                d = d[3:].decode('utf-16be')
                if d[:3] == u'\xa7\x31\x00': #modern protocol [u'127', u'1.7.4', u'A Minecraft Server', u'0', u'20']
                    segments = d[3:].split('\x00')
                    return server_ping(*segments)
                else: #1.2-era protocol [u'A Minecraft Server', u'0', u'20']
                    segments = d.split(u'\xa7')
                    return server_ping(None,self.server_milestone_long,*segments)
                    
            return error_ping
        else:
            if self.server_name in self.list_servers(self.base):
                return server_ping(None,None,self.server_properties['motd'::''],
                                   '0',self.server_properties['max-players'])
            else:
                raise RuntimeWarning('Server not found "%s"' % self.server_name)

    @property
    def sp(self):
        """Returns the entire server.properties in a dictionary"""
        return self.server_properties[:]

    @property
    def sc(self):
        """Returns the entire server.config in a dictionary"""
        return self.server_config[:]

    @property
    def server_type(self):
        """Returns best guess of server type"""
        return self._server_type

    @property
    def server_milestone(self):
        """Returns best guessed server major and minor versions"""
        jar_file = self.valid_filename(self.profile_config[self.profile:'run_as'])
        jar_path = os.path.join(self.env['cwd'], jar_file)
        return self.server_version(jar_path,
                                   self.profile_config[self.profile:'url']) or 'unknown'

    @property
    def server_milestone_long(self):
        """Returns best guessed server major, minor versions, release"""
        import re

        try:
            version = re.match(r'(\d)\.(\d)\.(\d)', self.server_milestone)
            return '%s.%s.%s' % (version.group(1), version.group(2), version.group(3))
        except (AttributeError, TypeError):
            return '0.0.0'

    @property
    def server_milestone_short(self):
        """Returns short version of server_milestone major/minor"""
        import re

        try:
            version = re.match(r'(\d)\.(\d)', self.server_milestone)
            return '%s.%s' % (version.group(1), version.group(2))
        except (AttributeError, TypeError):
            return '0.0'

    @property
    def ping_debug(self):
        """Returns helpful debug information for web-ui ping() issues"""
        return ' '.join([
            self.server_type,
            '(%s) -' % self.server_milestone_short,
            self.server_milestone,
            ])

# shell command constructor properties

    @property
    def previous_arguments(self):
        """Returns the dict used to construct a CLI command

        This method only works AFTER running the command_*
        and its primary use is to intercept incomplete commands
        in a wrapper before execution"""
        try:
            return self._previous_arguments
        except AttributeError:
            return {}

    @property
    @sanitize
    def command_start(self):
        """Returns the actual command used to start up a minecraft server."""
        required_arguments = {
            'screen_name': 'mc-%s' % self.server_name,
            'screen': self.BINARY_PATHS['screen'],
            'java': self.BINARY_PATHS['java'],
            'java_xmx': self.server_config['java':'java_xmx'],
            'java_xms': self.server_config['java':'java_xmx'],
            'java_tweaks': self.server_config['java':'java_tweaks':''],
            'java_debug': '',
            'jar_args': 'nogui'
            }

        from ConfigParser import NoOptionError

        try:
            jar_file = self.valid_filename(self.profile_config[self.profile:'run_as'])
            required_arguments['jar_file'] = os.path.join(self.env['cwd'], jar_file)
            required_arguments['jar_args'] = self.profile_config[self.profile:'jar_args':'']
        except (TypeError, ValueError):
            required_arguments['jar_file'] = None
            required_arguments['jar_args'] = None

        try:
            java_xms = self.server_config.getint('java','java_xms')
            if 0 < java_xms <= int(required_arguments['java_xmx']):
                required_arguments['java_xms'] = java_xms   
        except (NoOptionError, ValueError):
            pass

        try:
            if self.server_config.getboolean('java','java_debug'):
                required_arguments['java_debug'] = ' '.join([
                    '-verbose:gc',
                    '-XX:+PrintGCTimeStamps',
                    '-XX:+PrintGCDetails',
                    '-Xloggc:{0}'.format(os.path.join(self.env['cwd'], 'java_gc.log'))
                    ])
        except (NoOptionError, ValueError):
            pass

        self._previous_arguments = required_arguments
        return '%(screen)s -dmS %(screen_name)s ' \
               '%(java)s -server %(java_debug)s -Xmx%(java_xmx)sM -Xms%(java_xms)sM %(java_tweaks)s ' \
               '-jar %(jar_file)s %(jar_args)s' % required_arguments

    @property
    @sanitize
    def command_debug(self):
        """Returns the command used to test starting up a minecraft server."""
        import re
        
        command = self.command_start
        match = re.match(r'^.+ mc-.+? (.+)', command)
        return match.group(1)

    @property
    @sanitize
    def command_archive(self):
        """Returns the actual command used to archive a minecraft server.
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
        """Returns the actual command used to rdiff-backup a minecraft server."""
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
        """Returns the command to kill a pid"""
        required_arguments = {
            'kill': self.BINARY_PATHS['kill'],
            'pid': self.screen_pid
            }

        self._previous_arguments = required_arguments
        return '%(kill)s %(pid)s' % required_arguments

    @sanitize
    def command_restore(self, step, force):
        """Returns the actual command used to rdiff restore a minecraft server."""
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'force': '--force' if force else '',
            'step': step,
            'bwd': self.env['bwd'],
            'cwd': self.env['cwd']
            }

        self._previous_arguments = required_arguments
        return '%(rdiff)s %(force)s --restore-as-of %(step)s ' \
               '%(bwd)s %(cwd)s' % required_arguments

    @sanitize
    def command_prune(self, step):
        """Returns the actual command used to rdiff prune minecraft backups."""
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'step': step,
            'bwd': self.env['bwd']
            }

        if type(required_arguments['step']) is int:
            required_arguments['step'] = '%sB' % required_arguments['step']

        self._previous_arguments = required_arguments
        return '%(rdiff)s --force --remove-older-than %(step)s %(bwd)s' % required_arguments

    @property
    @sanitize
    def command_list_increments(self):
        """Returns the number of increments found at the backup dir"""
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'bwd': self.env['bwd']
            }

        self._previous_arguments = required_arguments
        return '%(rdiff)s --list-increments %(bwd)s' % required_arguments

    @property
    @sanitize
    def command_list_increment_sizes(self):
        """Returns the increment sizes found at the backup dir"""
        required_arguments = {
            'rdiff': self.BINARY_PATHS['rdiff-backup'],
            'bwd': self.env['bwd']
            }

        self._previous_arguments = required_arguments
        return '%(rdiff)s --list-increment-sizes %(bwd)s' % required_arguments

    @sanitize
    def command_wget_profile(self, profile, no_ca=False):
        """Returns the command to download a new file"""
        required_arguments = {
            'wget': self.BINARY_PATHS['wget'],
            'newfile': os.path.join(self.env['pwd'],
                                    profile,
                                    self.profile_config[profile:'save_as'] + '.new'),
            'url': self.profile_config[profile:'url'],
            'no_ca': '--no-check-certificate' if no_ca else ''
            }

        self._previous_arguments = required_arguments
        return '%(wget)s %(no_ca)s -O %(newfile)s %(url)s' % required_arguments

    @sanitize
    def command_apply_profile(self, profile):
        """Returns the command to copy profile files
        into the live working directory.
        """       
        required_arguments = {
            'profile': profile,
            'rsync': self.BINARY_PATHS['rsync'],
            'pwd': os.path.join(self.env['pwd']),
            'exclude': '',
            'cwd': '.'
            }

        try:
            files_to_exclude_str = self.profile_config[profile:'ignore']
        except (TypeError,KeyError):
            raise RuntimeError('Missing value in apply_profile command: %s' % str(required_arguments))
        else:
            if ',' in files_to_exclude_str:
                files = [f.strip() for f in files_to_exclude_str.split(',')]
            else:
                files = [f.strip() for f in files_to_exclude_str.split()]
            required_arguments['exclude'] = ' '.join("--exclude='%s'" % f for f in files)

        self._previous_arguments = required_arguments
        return '%(rsync)s -rlptD --chmod=ug+rw %(exclude)s %(pwd)s/%(profile)s/ %(cwd)s' % required_arguments

    @sanitize
    def command_delete_files(self, files):
        """Deletes files from present working directory"""       
        required_arguments = {
            'files': files,
            }

        self._previous_arguments = required_arguments
        return 'rm -- %(files)s' % required_arguments

    @property
    @sanitize
    def command_delete_server(self):
        """Deletes a server and all its related files and folders"""
        required_arguments = {
            'live': self.env['cwd'],
            'backup': self.env['bwd'],
            'archive': self.env['awd']
            }

        self._previous_arguments = required_arguments
        return 'rm -rf -- %(live)s %(backup)s %(archive)s' % required_arguments

    @sanitize
    def command_chown(self, user, path):
        """Executes chown on a directory"""
        required_arguments = {
            'user': user,
            'path': path
            }

        self._previous_arguments = required_arguments
        return 'chown -R %(user)s %(path)s' % required_arguments

    @sanitize
    def command_chgrp(self, group, path):
        """Executes chgrp on a directory"""
        required_arguments = {
            'group': group,
            'path': path
            }

        self._previous_arguments = required_arguments
        return 'chgrp -R %(group)s %(path)s' % required_arguments

#generator expressions

    @classmethod
    def list_servers(cls, base_directory):
        """Lists all directories in /servers/ and /backup/.
        Note: not all listings may be servers.
        """        
        from itertools import chain

        return list(set(chain(
            cls._list_subdirs(os.path.join(base_directory, cls.DEFAULT_PATHS['servers'])),
            cls._list_subdirs(os.path.join(base_directory, cls.DEFAULT_PATHS['backup']))
            )))

    @classmethod
    def list_ports_up(cls):
        """Returns IP address and port used by all live, running instances of Minecraft."""
        instance_connection = namedtuple('instance_connection', 'server_name port ip_address')
        for name, java, screen, base_dir in cls.list_servers_up():
            instance = cls(name, base_directory=base_dir)
            yield instance_connection(name, instance.port, instance.ip_address)

    def list_increments(self):
        """Returns a tuple of the timestamp of the most current mirror
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

    def list_increment_sizes(self):
        """Returns a list of the timestamps/sizes of all the increment files found.
        """
        from subprocess import CalledProcessError
        import re

        incs = namedtuple('increments', 'step timestamp increment_size cumulative_size')
        
        try:
            output = self._command_direct(self.command_list_increment_sizes, self.env['bwd'])
            assert output is not None
        except (CalledProcessError, AssertionError):
            raise StopIteration

        regex = re.compile(r'^(\w.*?) {3,}(.*?) {2,}([^ ]+ \w*)')
        count = 0

        for line in output.split('\n'):
            hits = regex.match(line)
            try:
                yield incs('%sB' % count, hits.group(1), hits.group(2), hits.group(3))
                count += 1
            except AttributeError:
                continue

    def list_archives(self):
        """Returns a list of the filenames/sizes of all archives found.
        """
        from time import ctime
        from procfs_reader import human_readable
        arcs = namedtuple('archives', 'filename size timestamp friendly_timestamp path')

        for i in self._list_files(self.env['awd']):
            info = os.stat(os.path.join(self.env['awd'], i))
            yield arcs(i,
                       info.st_size,
                       int(info.st_mtime),
                       ctime(info.st_mtime),
                       self.env['awd'])

    @classmethod
    def list_servers_up(cls):
        """Returns screen and java pid info for all running servers"""
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

        def find_base(directory, match_dir):
            pair = os.path.split(directory.rstrip('/'))
            if pair[1] == match_dir:
                return pair[0]
            elif not pair[1]:
                return ''
            else:
                return find_base(pair[0], match_dir)

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
            yield instance_pids(name,
                                java,
                                screen,
                                find_base(base, cls.DEFAULT_PATHS['servers']))

    def list_last_loglines(self, lines=100):
        """Returns last n lines from logfile"""
        from procfs_reader import tail

        try:
            with open(self.env['log'], 'rb') as log:
                return tail(log, int(lines))
        except IOError:
            pass
        return []

    @classmethod
    def list_servers_to_act(cls, action, base_directory):
        """Generator listing all servers doing action at this minute in time"""
        from procfs_reader import path_owner

        hits = []
        msm = cls.minutes_since_midnight()

        section_option = ('crontabs', '%s_interval' % action)

        for i in cls.list_servers(base_directory):
            try:
                path_ = os.path.join(base_directory, cls.DEFAULT_PATHS['servers'], i)
                owner_ = path_owner(path_)
                instance = cls(i, owner_, base_directory)
            
                interval = instance.server_config.getint(section_option[0],section_option[1])
                '''msm == 0; at midnight, always trigger. this works because
                if *_interval is not type(int), e.g., 'skip' or '',
                it'll except ValueError, skipping the test altogether'''
                if msm == 0:
                    hits.append(i)
                elif msm % interval == 0:
                    hits.append(i)
            except Exception:
                '''(ZeroDivisionError, KeyError, ValueError, NoOptionError, NoSectionError, OSError)'''
                continue

        return hits

    @classmethod
    def list_servers_start_at_boot(cls, base_directory):
        """Generator listing of all servers to start at boot"""
        from procfs_reader import path_owner

        hits = []
        for i in cls.list_servers(base_directory):
            try:
                path_ = os.path.join(base_directory, cls.DEFAULT_PATHS['servers'], i)
                owner_ = path_owner(path_)
                instance = cls(i, owner_, base_directory)
                if instance.server_config.getboolean('onreboot', 'start'):
                    hits.append(i)
            except Exception:
                '''(ValueError, KeyError, NoSectionError, NoOptionError)'''
                pass

        return hits

    @classmethod
    def list_servers_restore_at_boot(cls, base_directory):
        """Generator listing of all servers to restore at boot"""
        from procfs_reader import path_owner

        hits = []
        for i in cls.list_servers(base_directory):
            try:
                path_ = os.path.join(base_directory, cls.DEFAULT_PATHS['backup'], i)
                owner_ = path_owner(path_)
                instance = cls(i, owner_, base_directory)
                instance._load_config(load_backup=True)
                if instance.server_config.getboolean('onreboot', 'restore'):
                    hits.append(i)
            except Exception:
                '''(ValueError, KeyError, NoSectionError, NoOptionError)'''
                pass

        return hits

    @classmethod
    def list_profiles(cls, base_directory):
        """Lists all profiles found in profile.config at the base_directory root"""
        pc = config_file(os.path.join(base_directory, 'profiles', 'profile.config'))
        return pc[:]

    @staticmethod
    def _md5sum(filepath):
        """Returns the md5 sum of a file at filepath"""
        from hashlib import md5
        with open(filepath, 'rb') as infile:
            m = md5()
            m.update(infile.read())
            return m.hexdigest()

    @staticmethod
    def _mtime(filepath):
        """Returns the mtime of a file at filepath"""
        from time import ctime
        try:
            return ctime(os.path.getmtime(filepath))
        except os.error:
            return ''

#filesystem functions

    def _make_directory(self, path, do_raise=False):
        """Creates a directory and chowns it to self._owner.
        Fails silently.
        """
        try:
            os.makedirs(path)
        except OSError:
            if do_raise: raise
        else:
            os.chown(path, self.owner.pw_uid, self.owner.pw_gid)
            os.chmod(path, 0775)

    @staticmethod
    def has_ownership(username, path):
        """Returns username of owner, given provided username has access via fs"""
        from pwd import getpwuid, getpwnam
        from grp import getgrgid

        st = os.stat(path)
        uid = st.st_uid
        gid = st.st_gid

        owner_user = getpwuid(uid)
        owner_group = getgrgid(gid)
        user_info = getpwnam(username)

        if user_info.pw_uid == uid or \
           user_info.pw_gid == gid or \
           username in owner_group.gr_mem:
            return owner_user.pw_name
        elif username == 'root':
            return owner_user.pw_name
        else:
            raise OSError("User '%s' does not have permissions on %s" % (username, path))

    @classmethod
    def has_server_rights(cls, username, server_name, base_directory):
        """Checks whether a given username is owner/group of a server"""
        has_rights = False
        for d in ('servers', 'backup'):
            try:
                path_ = os.path.join(base_directory, cls.DEFAULT_PATHS[d], server_name)
                has_rights = cls.has_ownership(username, path_)
                break
            except OSError:
                pass
        return has_rights

    def chown(self, user):
        """Change the ownership of servers/backup/archive"""
        for d in ('cwd', 'bwd', 'awd'):
            self._make_directory(self.env[d])
            self._command_direct(self.command_chown(user, self.env[d]), self.env[d])

    def chgrp(self, group):
        """Change the group ownership of servers/backup/archive"""
        for d in ('cwd', 'bwd', 'awd'):
            self._make_directory(self.env[d])
            self._command_direct(self.command_chgrp(group, self.env[d]), self.env[d])

    def chgrp_pc(self, group):
        """Change the group ownership of profile.config"""
        self._command_direct('chgrp %s %s' % (group, self.env['pc']), self.env['pwd'])

    @staticmethod
    def _list_subdirs(directory):
        """Returns a list of all subdirectories of a path."""
        try:
            return os.walk(directory).next()[1]
        except StopIteration:
            return []

    @staticmethod
    def _list_files(directory):
        """Returns a list of all files in a path (no recursion)."""
        try:
            return os.walk(directory).next()[2]
        except StopIteration:
            return []

    @classmethod
    def _make_skeleton(cls, base_directory):
        """Creates the default paths at base_directory"""
        for d in cls.DEFAULT_PATHS:
            try:
                os.makedirs(os.path.join(base_directory, d))
            except OSError:
                pass

        try:
            path_ = os.path.join(base_directory, cls.DEFAULT_PATHS['profiles'], 'profile.config')
            with open(path_, 'a'): pass
        except IOError:
            pass
        else:
            try:
                os.chmod(path_, 0775)
            except OSError:
                pass

    @staticmethod
    def minutes_since_midnight():
        """Returns number of seconds since midnight"""
        from datetime import datetime
        now = datetime.now()
        return int(((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()) / 60)
