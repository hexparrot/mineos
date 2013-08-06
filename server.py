#!/usr/bin/env python2.7
"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import cherrypy
from json import dumps
from mineos import mc

class mc_server(object):
    METHODS = list(m for m in dir(mc) if callable(getattr(mc,m)) \
                   and not m.startswith('_'))
    PROPERTIES = list(m for m in dir(mc) if not callable(getattr(mc,m)) \
                      and not m.startswith('_'))

    def __init__(self, owner=None, base_directory=None):
        self.owner, self.base_directory = mc.valid_user(owner, base_directory)
        self.init_args = {
            'owner': self.owner.pw_name,
            'base_directory': self.base_directory
            }
    
    @cherrypy.expose
    def index(self):
        return 'hello!'

    @cherrypy.expose
    def command(self, **args):
        from subprocess import CalledProcessError
        
        args = {k:str(v) for k,v in args.iteritems()}
        server_name = args.pop('server_name', None)
        command = args.pop('cmd')

        response = {
            'result': None,
            'server_name': server_name,
            'cmd': command,
            'payload': None
            }

        retval = None

        try:
            if server_name:
                instance = mc(server_name, **self.init_args)
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
            else:
                if command == 'update_profile':
                    instance = mc('throwaway', **self.init_args)
                    retval = instance.update_profile(**args)
                elif command in self.METHODS:
                    import inspect
                    
                    try:
                        if 'base_directory' in inspect.getargspec(getattr(mc, command)).args:
                            retval = getattr(mc, command)(base_directory=self.init_args['base_directory'],
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
            import types
            response['result'] = 'success'
            
            if isinstance(retval, types.GeneratorType):
                retval = list(retval)
            elif hasattr(retval, '__dict__'):
                retval = dict(retval.__dict__)

        response['payload'] = retval
        return dumps(response)

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description='MineOS command line execution scripts',
                            version=__version__)
    parser.add_argument('-p',
                        dest='port',
                        help='the port to listen on',
                        default=8080)
    parser.add_argument('-i',
                        dest='ip_address',
                        help='the ip address to listen on',
                        default='0.0.0.0')
    parser.add_argument('-u',
                        dest='user',
                        help='the owner of the server process',
                        default=None)
    parser.add_argument('-d',
                        dest='base_directory',
                        help='the base of the mc file structure',
                        default=None)
    parser.add_argument('argv',
                        nargs='*',
                        help='additional arguments to pass to the command() function',
                        default=None)
    args = parser.parse_args()
    arguments = list(args.argv)

    cherrypy.server.socket_host = args.ip_address
    cherrypy.server.socket_port = int(args.port)
    cherrypy.quickstart(mc_server(args.user, args.base_directory))
