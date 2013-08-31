#!/usr/bin/env python2.7
"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import cherrypy
import inspect
import os
from json import dumps
from mineos import mc
from auth import AuthController, require

class ViewModel(object):
    def __init__(self, base_directory):
        from functools import partial
        
        self.base_directory = base_directory
        self.quick_create = partial(mc,
                                    base_directory=base_directory)

    def server_list(self):
        for i in mc.list_servers(self.base_directory):
            if mc.has_server_rights(cherrypy.session['_cp_username'],
                                    i,
                                    self.base_directory):
                yield i
            owner = False
        
    @cherrypy.expose
    def status(self):
        status = []
        for i in self.server_list():
            instance = self.quick_create(i, owner=cherrypy.session['_cp_username'])

            try:
                ping_info = instance.ping
            except KeyError:
                continue
            else:
                srv = {
                    'server_name': i,
                    'profile': instance.profile,
                    'up': instance.up,
                    'ip_address': instance.ip_address,
                    'port': instance.port,
                    'memory': instance.memory,
                    'java_xmx': instance.server_config['java':'java_xmx':'']
                    }
                srv.update(dict(instance.ping._asdict()))         
                status.append(srv)
        return dumps(status)
           
    @cherrypy.expose
    def profiles(self):
        md5s = {}

        for profile, opt_dict in mc.list_profiles(self.base_directory).iteritems():
            path = os.path.join(self.base_directory, 'profiles', profile)
            md5s[profile] = {}
            md5s[profile]['save_as'] = opt_dict['save_as']
            md5s[profile]['run_as'] = opt_dict['run_as']
            try:
                md5s[profile]['save_as_md5'] = mc._md5sum(os.path.join(path,opt_dict['save_as']))
                md5s[profile]['save_as_mtime'] = mc._mtime(os.path.join(path,opt_dict['save_as']))
            except IOError:
                md5s[profile]['save_as_md5'] = ''
                md5s[profile]['save_as_mtime'] = ''

            try:
                md5s[profile]['run_as_mtime'] = mc._mtime(os.path.join(path,opt_dict['run_as']))
                md5s[profile]['run_as_md5'] = mc._md5sum(os.path.join(path,opt_dict['run_as']))
            except IOError:
                md5s[profile]['run_as_mtime'] = ''
                md5s[profile]['run_as_md5'] = ''
            
        return dumps(md5s)     

    @cherrypy.expose
    def increments(self, server_name):
        instance = self.quick_create(server_name, owner=cherrypy.session['_cp_username'])
        return dumps([dict(d._asdict()) for d in instance.list_increment_sizes()])

    @cherrypy.expose
    def archives(self, server_name):
        instance = self.quick_create(server_name, owner=cherrypy.session['_cp_username'])
        return dumps([dict(d._asdict()) for d in instance.list_archives()])

    @cherrypy.expose
    def loadavg(self):
        from procfs_reader import proc_loadavg
        return dumps(proc_loadavg())

    @cherrypy.expose
    def dashboard(self):
        from procfs_reader import entries, proc_uptime, disk_usage
        
        kb_free = dict(entries('', 'meminfo'))['MemFree']
        mb_free = str(round(float(kb_free.split()[0])/1000, 2))
    
        return dumps({
            'uptime': str(proc_uptime()[0]),
            'memfree': mb_free,
            'whoami': cherrypy.session['_cp_username'],
            'df': dict(disk_usage('/')._asdict())
            })

    @cherrypy.expose
    def importable(self):
        path = os.path.join(self.base_directory, mc.DEFAULT_PATHS['import'])
        return dumps([{
            'path': path,
            'filename': f
            } for f in mc._list_files(path)])

class mc_server(object):    
    METHODS = list(m for m in dir(mc) if callable(getattr(mc,m)) \
                   and not m.startswith('_'))
    PROPERTIES = list(m for m in dir(mc) if not callable(getattr(mc,m)) \
                      and not m.startswith('_'))

    def __init__(self, script_directory, base_directory):
        self.script_directory = script_directory
        self.base_directory = base_directory
        self.vm = ViewModel(self.base_directory)

    @cherrypy.expose
    @require()
    def index(self):
        from cherrypy.lib.static import serve_file
        return serve_file(os.path.join(self.script_directory, 'index.html'))

    @require()
    def methods(self):
        return dumps(self.METHODS)

    @require()
    def properties(self):
        return dumps(self.PROPERTIES)

    @require()
    def inspect_method(self, method):
        try:
            target = getattr(mc, method).func_closure[0].cell_contents
            reqd = inspect.getargspec(target).args
        except TypeError:
            try:
                reqd = inspect.getargspec(getattr(mc, method)).args
            except TypeError:
                return dumps([])
        except AttributeError:
            reqd = ['server_name', 'command']

        if "self" in reqd:
            reqd[reqd.index("self")] = "server_name"
        elif "cls" in reqd:
            del reqd[reqd.index("cls")]

        return dumps(reqd)
                 
    @cherrypy.expose
    @require()
    def host(self, **args):
        from subprocess import CalledProcessError
        
        args = {k:str(v) for k,v in args.iteritems()}
        command = args.pop('cmd')

        retval = None
        response = {
            'result': None,
            'cmd': command,
            'payload': None
            }

        init_args = {
            'owner': cherrypy.session['_cp_username'],
            'base_directory': self.base_directory
            }

        try:
            if command == 'define_profile':
                from json import loads
                from urllib import unquote

                definition_unicode = loads(args['profile'])
                definition = {str(k):str(v) for k,v in definition_unicode.iteritems()}

                definition['url'] = unquote(definition['url'])

                instance = mc('throwaway', **init_args)
                retval = instance.define_profile(definition)      
            elif command == 'update_profile':
                instance = mc('throwaway', **init_args)
                retval = instance.update_profile(**args)
            elif command == 'remove_profile':
                instance = mc('throwaway', **init_args)
                retval = instance.remove_profile(**args)
            elif command == 'stock_profile':
                from stock_profiles import STOCK_PROFILES
                
                profile = STOCK_PROFILES[args['profile']]
                mc('throwaway', **init_args).define_profile(profile)
                retval = '%s profile created' % profile['name']
            elif command in self.METHODS:                
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
        except (RuntimeError, KeyError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        except CalledProcessError, ex:
            response['result'] = 'error'
            retval = ex.output
        else:
            response['result'] = 'success'

        response['payload'] = self.to_jsonable_type(retval)
        return dumps(response)

    @cherrypy.expose
    @require()
    def create(self, **args):
        args = {k:str(v) for k,v in args.iteritems()}
        server_name = args.pop('server_name')
        command = args.pop('cmd')
        try:
            group = args.pop('group')
        except KeyError:
            group = None

        retval = None
        response = {
            'result': None,
            'server_name': server_name,
            'cmd': command,
            'payload': None
            }

        from json import loads
        from collections import defaultdict
        from grp import getgrnam

        try:
            try:
                if group and cherrypy.session['_cp_username'] not in getgrnam(group).gr_mem:
                    raise OSError("Create server aborted: " \
                                  "%s does not belong to group '%s'" % (cherrypy.session['_cp_username'],
                                                                        group))
            except KeyError:
                raise OSError('Group not found: %s' % group)
            
            instance = mc(server_name,
                          cherrypy.session['_cp_username'],
                          base_directory=self.base_directory)
            sp_unicode = loads(args['sp'])
            sc_unicode = loads(args['sc'])

            sp = {str(k):str(v) for k,v in sp_unicode.iteritems()}
            
            sc = defaultdict(dict)
            for section in sc_unicode.keys():
                for key in sc_unicode[section].keys():
                    sc[str(section)][str(key)] = str(sc_unicode[section][key])
            
            instance.create(dict(sc),sp)
            if group:
                instance.chgrp(group)
        except (RuntimeError, KeyError, OSError, ValueError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'
            retval = "Server '%s' successfully created" % server_name

        response['payload'] = self.to_jsonable_type(retval)
        return dumps(response)

    @cherrypy.expose
    @require()
    def import_server(self, **args):
        args = {k:str(v) for k,v in args.iteritems()}
        server_name = args.pop('server_name')
        command = args.pop('cmd')

        retval = None
        response = {
            'result': None,
            'server_name': server_name,
            'cmd': command,
            'payload': None
            }

        from json import loads
        from collections import defaultdict

        try:
            instance = mc(server_name,
                          cherrypy.session['_cp_username'],
                          base_directory=self.base_directory)

            instance.import_server(**args)
            for d in ('cwd', 'bwd', 'awd'):
                instance._make_directory(instance.env[d])
        except (RuntimeError, KeyError, OSError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        else:
            response['result'] = 'success'
            retval = "Server '%s' successfully imported" % server_name

        response['payload'] = self.to_jsonable_type(retval)
        return dumps(response)

    @cherrypy.expose
    @require()
    def server(self, **args):
        from subprocess import CalledProcessError

        args = {k:str(v) for k,v in args.iteritems()}
        server_name = args.pop('server_name')
        command = args.pop('cmd')

        retval = None
        response = {
            'result': None,
            'server_name': server_name,
            'cmd': command,
            'payload': None
            }

        try:
            instance = None

            approved_user = mc.has_server_rights(cherrypy.session['_cp_username'],
                                                 server_name,
                                                 self.base_directory)

            if approved_user:
                path_ = os.path.join(self.base_directory, mc.DEFAULT_PATHS['servers'], server_name)
                instance = mc(server_name,
                              approved_user,
                              base_directory=self.base_directory)
            else:
                raise OSError('%s does not have sufficient rights to %s' % \
                              (cherrypy.session['_cp_username'], server_name))
             
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
        except (RuntimeError, KeyError, OSError) as ex:
            response['result'] = 'error'
            retval = ex.message
        except RuntimeWarning as ex:
            response['result'] = 'warning'
            retval = ex.message
        except CalledProcessError, ex:
            response['result'] = 'error'
            retval = ex.output
        else:
            response['result'] = 'success'

        response['payload'] = self.to_jsonable_type(retval)
        return dumps(response)

    @staticmethod
    def to_jsonable_type(retval):
        import types

        if isinstance(retval, types.GeneratorType):
            return list(retval)
        elif hasattr(retval, '__dict__'):
            return dict(retval.__dict__)
        else:
            return retval

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description='MineOS web user interface service',
                            version=__version__)
    parser.add_argument('-p',
                        dest='port',
                        help='the port to listen on',
                        default=8080)
    parser.add_argument('-i',
                        dest='ip_address',
                        help='the ip address to listen on',
                        default='0.0.0.0')
    parser.add_argument('-d',
                        dest='base_directory',
                        help='the base of the mc file structure',
                        default=None)
    parser.add_argument('--http',
                        action='store_true',
                        help='use HTTP not HTTPS.',
                        default=None)
    parser.add_argument('--debug',
                        action='store_true',
                        default=False,
                        help='enable logging to the stdout')
    parser.add_argument('-s',
                        dest='cert_files',
                        help='certificate files: /etc/ssl/certs/cert.crt,/etc/ssl/certs/cert.key',
                        default=None)
    parser.add_argument('-c',
                        dest='cert_chain',
                        help='CA certificate chain: /etc/ssl/certs/cert-chain.crt',
                        default=None)
    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))

    global_conf = { 
            'server.socket_host': args.ip_address,
            'server.socket_port': int(args.port),
            'tools.sessions.on': True,
            'tools.auth.on': True,
            'log.screen': args.debug
            }

    if not args.http:
        if args.cert_files:
            ssl = {
                'server.ssl_module': 'builtin',
                'server.ssl_certificate': args.cert_files.split(',')[0].strip(),
                'server.ssl_private_key': args.cert_files.split(',')[1].strip(),
                }
        else:
            if os.path.isfile('/etc/ssl/certs/mineos.crt') and \
               os.path.isfile('/etc/ssl/certs/mineos.key'):
                ssl = {
                    'server.ssl_module': 'builtin',
                    'server.ssl_certificate': '/etc/ssl/certs/mineos.crt',
                    'server.ssl_private_key': '/etc/ssl/certs/mineos.key',
                    }
            else:
                ssl = {
                    'server.ssl_module': 'builtin',
                    'server.ssl_certificate': 'mineos.crt',
                    'server.ssl_private_key': 'mineos.key',
                    }  
        if args.cert_chain:
            ssl.update({'server.ssl_certificate_chain': args.cert_chain.strip()})
        else:
            ssl.update({'server.ssl_ca_certificate': None})
        global_conf.update(ssl)

    static_conf = {
        '/assets': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'assets')
            },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'css')
            },
        '/img': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'img')
            },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'js')
            }
        }

    auth_conf = {
        '/login': {
            'tools.staticfile.filename': 'login.html'
            }
        }
        
    from getpass import getuser
    base_dir = args.base_directory or mc.valid_user(getuser())[1]
    mc._make_skeleton(base_dir) 

    if not args.debug:
        from cherrypy.process.plugins import Daemonizer
        Daemonizer(cherrypy.engine).subscribe()

    cherrypy.config.update(global_conf)
    cherrypy.tree.mount(mc_server(current_dir, base_dir), "/", config=static_conf)
    cherrypy.tree.mount(AuthController(current_dir), '/auth', config=auth_conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
