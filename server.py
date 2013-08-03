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
        args = {k:str(v) for k,v in args.iteritems()}
        server_name = args.pop('server_name', None)
        command = args.pop('cmd')

        if server_name:
            if command in self.METHODS:
                instance = mc(server_name)
                retval = getattr(instance, command)(**args)
                if retval:
                    if isinstance(retval, types.GeneratorType):
                        return dumps(list(retval))
                    else:
                        return dumps(retval)
                return dumps(args)
            elif command in self.PROPERTIES:
                instance = mc(server_name)
                if args:
                    return dumps(setattr(instance, command, args.values()[0]))
                else:
                    return dumps(getattr(instance, command))
        else:
            if command in self.METHODS:
                try:
                    retval = getattr(mc, command)(**args)
                    if retval: return dumps(retval)
                except TypeError:
                    instance = mc('throwaway')
                    retval = getattr(instance, command)(**args)
                    if retval:
                        return dumps(retval)

        return dumps(args)

cherrypy.server.socket_host = '0.0.0.0'
cherrypy.quickstart(mc_server())
