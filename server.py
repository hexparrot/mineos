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
                instance = mc(server_name)
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
                    instance = mc('throwaway')
                    retval = instance.update_profile(**args)
                elif command in self.METHODS:
                    try:
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

cherrypy.server.socket_host = '0.0.0.0'
cherrypy.quickstart(mc_server())
