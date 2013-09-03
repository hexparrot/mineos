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
import auth
from mineos import mc

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
    parser.add_argument('--daemon',
                        action='store_true',
                        default=False,
                        help='run server as a daemon')
    parser.add_argument('-s',
                        dest='cert_files',
                        help='certificate files: /etc/ssl/certs/cert.crt,/etc/ssl/certs/cert.key',
                        default=None)
    parser.add_argument('-c',
                        dest='cert_chain',
                        help='CA certificate chain: /etc/ssl/certs/cert-chain.crt',
                        default=None)
    args = parser.parse_args()

    from getpass import getuser
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = args.base_directory or mc.valid_user(getuser())[1]
    mc._make_skeleton(base_dir) 

    log_error = '/var/log/mineos.log'
    
    try:
        with open(log_error, 'a'): pass
    except IOError:
        log_error = os.path.join(base_dir, 'mineos.log')

    global_conf = {
        'server.socket_host': args.ip_address,
        'server.socket_port': int(args.port),
        'tools.sessions.on': True,
        'tools.auth.on': True,
        'log.screen': not args.daemon,
        'log.error_file': log_error
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

    root_conf = {
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

    empty_conf = {
        '/': {}
        }

    if args.daemon:
        from cherrypy.process.plugins import Daemonizer
        Daemonizer(cherrypy.engine).subscribe()

    import mounts

    cherrypy.config.update(global_conf)
    cherrypy.tree.mount(mounts.Root(current_dir, base_dir), "/", config=root_conf)
    cherrypy.tree.mount(mounts.ViewModel(base_dir), "/vm", config=empty_conf)
    cherrypy.tree.mount(auth.AuthController(current_dir), '/auth', config=empty_conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
