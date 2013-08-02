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
    parser.add_argument('-u',
                        dest='user',
                        help='alternate user than current',
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
    args.cmd = args.cmd.lower()
    arguments = list(args.argv)

    available_methods = list(m for m in dir(mc) if callable(getattr(mc,m)) \
                             and not m.startswith('_'))
    available_properties = list(m for m in dir(mc) if not callable(getattr(mc,m)) \
                                and not m.startswith('_'))

    import pprint, types
    pp = pprint.PrettyPrinter(indent=4)

    if args.server_name:
        init_args = {
            'server_name': args.server_name,
            'owner': args.user,
            'base_directory': args.base_directory
            }

        if args.cmd in ['screen', 'console']:
            import os
            instance = mc(**init_args)
            os.system('screen -r %s' % instance.screen_pid)
        elif args.cmd in available_methods:
            instance = mc(**init_args)
            retval = getattr(instance, args.cmd)(*arguments)
            if retval:
                if isinstance(retval, types.GeneratorType):
                    pp.pprint(list(retval))
                else:
                    pp.pprint(retval)
            else:
                print '{%s} completed successfully.' % args.cmd
        elif args.cmd in available_properties:
            instance = mc(**init_args)
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
            instance = mc(**init_args)
            text = '%s %s' % (args.cmd, ' '.join(arguments))
            instance._command_stuff(text)
            print '{%s} sent to gameserver console [screen_pid:%s] successfully.' % (text,
                                                                                    instance.screen_pid)
    else:
        init_args = {
            'server_name': 'throwaway',
            'owner': args.user,
            'base_directory': args.base_directory
            }
        arguments = list(args.argv)

        if args.cmd == 'update_profile':
            mc(**init_args).update_profile(*arguments)
        elif args.cmd == 'stock_profile':
            if arguments[0] == 'vanilla':
                profile = {
                    'name': 'vanilla',
                    'type': 'standard_jar',
                    'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
                    'save_as': 'minecraft_server.jar',
                    'run_as': 'minecraft_server.jar',
                    'ignore': '',
                    }
                mc(**init_args).define_profile(profile)
            else:
                raise NotImplementedError
        elif args.cmd == 'define_profile':
            from collections import OrderedDict
            profile = OrderedDict([(k,None) for k in ('name', 'type', 'url',
                                                      'save_as', 'run_as','ignore')])
            for k,v in profile.iteritems():
                profile[k] = raw_input('%s: ' % k)
            
            mc(**init_args).define_profile(profile)
        elif args.cmd in available_methods:
            retval = getattr(mc, args.cmd)(*arguments)
            if retval:
                if isinstance(retval, types.GeneratorType):
                    pp.pprint(list(retval))
                else:
                    pp.pprint(retval)
            else:
                print '{%s} completed without error.' % args.cmd
        else:
            raise NotImplementedError
            
            
