#!/usr/bin/env python2.7
"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

if __name__=="__main__":
    from mineos import mc
    from argparse import ArgumentParser

    parser = ArgumentParser(description='MineOS command line execution scripts',
                            version=__version__)
    parser.add_argument('cmd',
                        help='the command to execute')
    parser.add_argument('-s',
                        dest='server_name',
                        help='the server to act upon')
    parser.add_argument('argv',
                        nargs='*',
                        help='additional arguments to pass to the command() function',
                        default=None)
    parser.add_argument('--force', dest='force', action='store_const',
                       const=True, default=False,
                       help='force the action to take place, e.g., restore')
    parser.add_argument('--debug', dest='debug', action='store_const',
                       const=True, default=False,
                       help='show full traceback output')
    args = parser.parse_args()
    args.cmd = args.cmd.lower()

    if args.server_name:
        arguments = list(args.argv)
        available_methods = list(m for m in dir(mc) if callable(getattr(mc,m)) \
                                 and not m.startswith('_'))
        available_properties = list(m for m in dir(mc) if not callable(getattr(mc,m)) \
                                    and not m.startswith('_'))

        import types, pprint
        pp = pprint.PrettyPrinter(indent=4)

        if args.cmd in available_methods:
            instance = mc(args.server_name)
            retval = getattr(instance, args.cmd)(*arguments)
            if retval:
                if isinstance(retval, types.GeneratorType):
                    pp.pprint(list(retval))
                else:
                    pp.pprint(retval)
            else:
                print '{%s} completed without error.' % args.cmd
        elif args.cmd in available_properties:
            instance = mc(args.server_name)
            try:
                previous_value = getattr(instance, args.cmd)
                setattr(instance, args.cmd, arguments[0])
                print 'previous value:'
                pp.pprint(previous_value)
                print 'current value:'
                pp.pprint(getattr(instance, args.cmd))
            except IndexError:
                pp.pprint(getattr(instance, args.cmd))            
        else:
            instance = mc(args.server_name)
            text = '%s %s' % (args.cmd, ' '.join(arguments))
            instance._command_stuff(text)
            print '{%s} sent to gameserver console [screen_pid:%s] successfully.' % (text,
                                                                                    instance.screen_pid)
    else:
        arguments = list(args.argv)

        if args.cmd == 'update_profile':
            #this logic branch is not suited for /var/games
            instance = mc('throwaway')
            instance.update_profile(arguments[0])
        elif args.cmd == 'define_profile':
            if arguments[0] == 'vanilla':
                profile = {
                    'name': 'vanilla',
                    'type': 'standard_jar',
                    'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
                    'save_as': 'minecraft_server.jar',
                    'run_as': 'minecraft_server.jar',
                    'action': 'download',
                    'ignore': '',
                    }
                instance = mc('throwaway')
                instance.define_profile(profile)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
            
            
