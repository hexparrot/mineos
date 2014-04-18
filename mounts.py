#!/usr/bin/env python2.7
"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import cherrypy
import os
from mineos import mc
from auth import require
from subprocess import CalledProcessError

def to_jsonable_type(retval):
    import types

    if isinstance(retval, types.GeneratorType):
        return list(retval)
    elif hasattr(retval, '__dict__'):
        return dict(retval.__dict__)
    else:
        return retval

class ViewModel(object):
    def __init__(self):
        self.base_directory = cherrypy.config['misc.base_directory']

    @property
    def login(self):
        return str(cherrypy.session['_cp_username'])

    def server_list(self):
        for i in mc.list_servers(self.base_directory):
            if mc.has_server_rights(self.login, i, self.base_directory):
                yield i

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def status(self):
        servers = []
        for i in self.server_list():
            instance = mc(i, self.login, self.base_directory)

            try:
                java_xmx = int(instance.server_config['java':'java_xmx'])
            except (KeyError, ValueError):
                java_xmx = 0

            srv = {
                'server_name': i,
                'profile': instance.profile,
                'up': instance.up,
                'ip_address': instance.ip_address,
                'port': instance.port,
                'memory': instance.memory,
                'java_xmx': java_xmx
                }

            try:
                ping = instance.ping
            except KeyError:
                continue
            except IndexError:
                #assert d[0] == '\xff'
                #IndexError: string index out of range
                srv.update({
                    'protocol_version': '',
                    'server_version': '',
                    'motd': '',
                    'players_online': -1,
                    'max_players': instance.server_properties['max-players'::0]
                    })
            else:
                srv.update(dict(instance.ping._asdict()))
                
            servers.append(srv)

        return servers

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def profiles(self):
        def pdict():
            for profile, opt_dict in mc.list_profiles(self.base_directory).iteritems():
                path_ = os.path.join(self.base_directory, 'profiles', profile)
                run_as = os.path.join(path_,opt_dict['run_as'])
                save_as = os.path.join(path_,opt_dict['save_as'])
                
                profile_info = opt_dict
                profile_info['profile'] = profile

                if 'url' in profile_info:
                    profile_info['version'] = mc.server_version(run_as, profile_info['url'])
                else:
                    profile_info['url'] = ''
                    profile_info['version'] = ''
                
                try:
                    profile_info['save_as_md5'] = mc._md5sum(save_as)
                    profile_info['save_as_mtime'] = mc._mtime(save_as)
                except IOError:
                    profile_info['save_as_md5'] = ''
                    profile_info['save_as_mtime'] = ''
                    
                try:
                    profile_info['run_as_mtime'] = mc._mtime(run_as)
                    profile_info['run_as_md5'] = mc._md5sum(run_as)
                except IOError:
                    profile_info['run_as_mtime'] = ''
                    profile_info['run_as_md5'] = ''

                yield profile_info
                
        return list(pdict())

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def increments(self, server_name):
        instance = mc(server_name, self.login, self.base_directory)
        return [dict(d._asdict()) for d in instance.list_increment_sizes()]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def archives(self, server_name):
        instance = mc(server_name, self.login, self.base_directory)
        return [dict(d._asdict()) for d in instance.list_archives()]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def server_summary(self, server_name):
        from procfs_reader import disk_usage
        from pwd import getpwuid
        from grp import getgrgid

        cwd = os.path.join(self.base_directory, mc.DEFAULT_PATHS['servers'], server_name)
        bwd = os.path.join(self.base_directory, mc.DEFAULT_PATHS['backup'], server_name)
        awd = os.path.join(self.base_directory, mc.DEFAULT_PATHS['archive'], server_name)
        st = os.stat(cwd)

        dir_info = {
            'owner': getpwuid(st.st_uid).pw_name,
            'group': getgrgid(st.st_gid).gr_name
            #'du_bwd': disk_usage(bwd),
            #'du_awd': disk_usage(awd)
            }

        try:
            dir_info['du_cwd'] = disk_usage(cwd)
        except:
            dir_info['du_cwd'] = 0

        return dir_info
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def loadavg(self):
        from procfs_reader import proc_loadavg
        return proc_loadavg()     
                    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def dashboard(self):
        from procfs_reader import entries, proc_uptime, disk_free, git_hash
        from grp import getgrall, getgrgid
        from pwd import getpwnam
        from stock_profiles import STOCK_PROFILES
        
        kb_free = dict(entries('', 'meminfo'))['MemFree']
        mb_free = str(round(float(kb_free.split()[0])/1000, 2))

        try:
            pc_path = os.path.join(self.base_directory, mc.DEFAULT_PATHS['profiles'], 'profile.config')
            mc.has_ownership(self.login, pc_path)
        except (OSError, KeyError):
            profile_editable = False
        else:
            profile_editable = True
        finally:
            st = os.stat(pc_path)
            pc_group = getgrgid(st.st_gid).gr_name

        primary_group = getgrgid(getpwnam(self.login).pw_gid).gr_name
    
        return {
            'uptime': int(proc_uptime()[0]),
            'memfree': mb_free,
            'whoami': self.login,
            'group': primary_group,
            'df': dict(disk_free('/')._asdict()),
            'groups': [i.gr_name for i in getgrall() if self.login in i.gr_mem or self.login == 'root'] + [primary_group],
            'pc_permissions': profile_editable,
            'pc_group': pc_group,
            'git_hash': git_hash(os.path.dirname(os.path.abspath(__file__))),
            'stock_profiles': [i['name'] for i in STOCK_PROFILES],
            'base_directory': self.base_directory,
            }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def importable(self):
        path = os.path.join(self.base_directory, mc.DEFAULT_PATHS['import'])
        return [{
            'path': path,
            'filename': f
            } for f in mc._list_files(path)]

class Root(object):
    METHODS = list(m for m in dir(mc) if callable(getattr(mc,m)) \
                   and not m.startswith('_'))
    PROPERTIES = list(m for m in dir(mc) if not callable(getattr(mc,m)) \
                      and not m.startswith('_'))

    def __init__(self):
        self.html_directory = cherrypy.config['misc.html_directory']
        self.base_directory = cherrypy.config['misc.base_directory']

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def webui_config(self):
        return {k.lstrip('webui.'):v for k,v in cherrypy.config.iteritems() if k.startswith('webui.')}

    @property
    def login(self):
        return str(cherrypy.session['_cp_username'])

    @cherrypy.expose
    @require()
    def index(self):
        from cherrypy.lib.static import serve_file

        try:
            return serve_file(os.path.join(self.html_directory,
                                           'index_%s.html' % cherrypy.config['misc.localization']))
        except cherrypy.NotFound:
            return serve_file(os.path.join(self.html_directory,
                                           'index_en.html'))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def host(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        command = args.pop('cmd')
        retval = None

        response = {
            'result': None,
            'cmd': command,
            'payload': None
            }

        try:
            if command == 'define_profile':
                mc.has_ownership(self.login, os.path.join(self.base_directory,
                                                          mc.DEFAULT_PATHS['profiles'],
                                                          'profile.config'))

                from json import loads
                from urllib import unquote

                definition_unicode = loads(args['profile_dict'])
                definition = {str(k):str(v) for k,v in definition_unicode.iteritems()}

                try:
                    definition['url'] = unquote(definition['url'])
                except KeyError:
                    pass

                if definition['name'] in mc.list_profiles(self.base_directory).keys():
                    raise KeyError('Profiles may not be modified once created')

                instance = mc('throwaway', None, self.base_directory)
                retval = instance.define_profile(definition)                
            elif command == 'update_profile':
                mc.has_ownership(self.login, os.path.join(self.base_directory,
                                                           mc.DEFAULT_PATHS['profiles'],
                                                           'profile.config'))
                 
                instance = mc('throwaway', None, self.base_directory)
                retval = instance.update_profile(**args)
            elif command == 'remove_profile':
                for i in mc.list_servers(self.base_directory):
                    if mc(i, None, self.base_directory).profile == args['profile']:
                        raise KeyError('May not remove profiles in use by 1 or more servers')
                
                instance = mc('throwaway', None, self.base_directory)
                retval = instance.remove_profile(**args)
            elif command == 'stock_profile':
                from stock_profiles import STOCK_PROFILES
                
                profile = iter([i for i in STOCK_PROFILES if i['name'] == args['profile']]).next()
                mc('throwaway', None, self.base_directory).define_profile(profile)
                retval = '%s profile created' % profile['name']
            elif command == 'modify_profile':
                mc('throwaway', None, self.base_directory).modify_profile(args['option'],args['value'],args['section'])
                retval = '%s profile updated' % args['section']
            elif command in self.METHODS:
                import inspect
                try:
                    if 'base_directory' in inspect.getargspec(getattr(mc, command)).args:
                        retval = getattr(mc, command)(base_directory=init_args['base_directory'],
                                                      **args)
                    else:
                        retval = getattr(mc, command)(**args)
                except TypeError as ex:
                    raise RuntimeError(ex.message)
            else:
                raise RuntimeWarning('Command not found: should this be to a server?')
        except (RuntimeError, KeyError, OSError, NotImplementedError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'

        response['payload'] = to_jsonable_type(retval)
        return response

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def server(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        command = args.pop('cmd')
        server_name = args.pop('server_name')
        retval = None

        response = {
            'result': None,
            'cmd': command,
            'payload': None
            }

        owner = mc.has_server_rights(self.login, server_name, self.base_directory)

        try:
            if server_name is None:
                raise KeyError('Required value missing: server_name')
            elif not owner:
                raise OSError('User %s does not have permissions on %s' % (self.login, server_name))
            
            instance = mc(server_name, owner, self.base_directory)

            if command in self.METHODS:
                retval = getattr(instance, command)(**args)
            elif command in self.PROPERTIES:
                if args:
                    setattr(instance, command, args.values()[0])
                    retval = args.values()[0]
                else:
                    retval = getattr(instance, command)
            else:
                instance._command_stuff(command)
                retval = '"%s" successfully sent to server.' % command
        except (RuntimeError, KeyError, NotImplementedError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'

        response['payload'] = to_jsonable_type(retval)
        return response

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def logs(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        server_name = args.pop('server_name')
        retval = None

        response = {
            'result': None,
            'cmd': 'logs',
            'payload': None
            }

        try:
            instance = mc(server_name, self.login, self.base_directory)

            if 'log_offset' not in cherrypy.session or 'reset' in args:
                cherrypy.session['log_offset'] = os.stat(instance.env['log']).st_size
                retval = instance.list_last_loglines(100)
            elif not cherrypy.session['log_offset']:
                cherrypy.session['log_offset'] = os.stat(instance.env['log']).st_size
                retval = instance.list_last_loglines(100)
            elif cherrypy.session['log_offset']:
                with open(instance.env['log'], 'rb') as log:
                    log.seek(cherrypy.session['log_offset'], 0)
                    retval = log.readlines()
                    cherrypy.session['log_offset'] = os.stat(instance.env['log']).st_size
        except (RuntimeError, KeyError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except (RuntimeWarning, OSError) as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'

        response['payload'] = to_jsonable_type(retval)
        return response
        
    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def create(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        server_name = args.pop('server_name')
        group = args.pop('group', None)
        retval = None

        response = {
            'result': None,
            'cmd': 'create',
            'payload': None
            }

        from json import loads
        from collections import defaultdict
        from grp import getgrnam
        from stat import S_IWGRP

        try:
            group_info = None
            if group:
                try:
                    group_info = getgrnam(group)
                except KeyError:
                    raise KeyError("There is no group '%s'" % group)
                else:
                    if self.login not in group_info.gr_mem and self.login != group_info.gr_name:
                        raise OSError("user '%s' is not part of group '%s'" % (self.login, group))
            
            instance = mc(server_name, self.login, self.base_directory)
            sp_unicode = loads(args['sp'])
            sc_unicode = loads(args['sc'])
            
            sp = {str(k):str(v) for k,v in sp_unicode.iteritems()}
            sc = defaultdict(dict)
            
            for section in sc_unicode.keys():
                for key in sc_unicode[section].keys():
                    sc[str(section)][str(key)] = str(sc_unicode[section][key])
            
            instance.create(dict(sc),sp)
            if group:
                for d in ('servers', 'backup', 'archive'):
                    path_ = os.path.join(self.base_directory, mc.DEFAULT_PATHS[d], server_name)
                    os.lchown(path_, -1, group_info.gr_gid)
        except (RuntimeError, KeyError, OSError, ValueError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'

        response['payload'] = to_jsonable_type(retval)
        return response

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def import_server(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        server_name = args.pop('server_name')
        retval = None

        response = {
            'result': None,
            'cmd': 'import_server',
            'payload': None
            }

        from pwd import getpwnam
        from grp import getgrgid

        try:
            instance = mc(server_name, self.login, self.base_directory)
            instance.import_server(**args)
            instance = mc(server_name, None, self.base_directory)
            instance.chown(self.login)
            instance.chgrp(getgrgid(getpwnam(self.login).pw_gid).gr_name)
        except (RuntimeError, KeyError, OSError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'
            retval = "Server '%s' successfully imported" % server_name

        response['payload'] = to_jsonable_type(retval)
        return response 

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def change_group(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        server_name = args.pop('server_name')
        group = args.pop('group')
        retval = None

        response = {
            'result': None,
            'cmd': 'chgrp',
            'payload': None
            }

        try:
            if self.login == mc.has_server_rights(self.login, server_name, self.base_directory) or \
               self.login == 'root':
                instance = mc(server_name, None, self.base_directory)
                instance.chgrp(group)
            else:
                raise OSError('Group assignment to %s failed. Only the owner make change groups.' % group)
        except (RuntimeError, KeyError, OSError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'
            retval = "Server '%s' group ownership granted to '%s'" % (server_name, group)

        response['payload'] = to_jsonable_type(retval)
        return response 

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def change_pc_group(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        group = args.pop('group')
        retval = None

        response = {
            'result': None,
            'cmd': 'chgrp_pc',
            'payload': None
            }

        try:
            if self.login == 'root':
                instance = mc('throwaway', None, self.base_directory)
                instance.chgrp_pc(group)
            else:
                raise OSError('Group assignment to %s failed. Only the superuser may make change groups.' % group)
        except (RuntimeError, KeyError, OSError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'
            retval = "profile.config group ownership granted to '%s'" % group

        response['payload'] = to_jsonable_type(retval)
        return response 

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @require()
    def delete_server(self, **raw_args):
        args = {k:str(v) for k,v in raw_args.iteritems()}
        server_name = args.pop('server_name')
        retval = None

        response = {
            'result': None,
            'cmd': 'delete_server',
            'payload': None
            }

        try:
            if mc.has_server_rights(self.login, server_name, self.base_directory):
                instance = mc(server_name, None, self.base_directory)
                instance.delete_server()
            else:
                raise OSError('Server deletion failed. Only the server owner or root may delete servers.')
        except (RuntimeError, KeyError, OSError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except CalledProcessError as ex:
            response['result'] = 'error'
            retval = ex.output
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'
            retval = "Server '%s' deleted" % server_name

        response['payload'] = to_jsonable_type(retval)
        return response     
