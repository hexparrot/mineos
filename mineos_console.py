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
    from getpass import getuser
    import os

    parser = ArgumentParser(description='MineOS command line execution scripts',
                            version=__version__)
    parser.add_argument('cmd',
                        help='the command to execute')
    parser.add_argument('-s',
                        dest='server_name',
                        help='the server to act upon')
    parser.add_argument('-d',
                        dest='base_directory',
                        help='the base of the mc file structure',
                        default='/var/games/minecraft')
    parser.add_argument('--this',
                        action='store_true',
                        default=False,
                        help='use pwd to determine -d and -s values')
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

    if args.this:
        args.server_name = os.path.basename(os.getcwd())
        args.base_directory = os.path.dirname(os.path.dirname(os.getcwd()))
    else:
        args.base_directory = args.base_directory or os.path.expanduser("~")
        mc._make_skeleton(args.base_directory)

    if args.server_name:
        owner = mc.has_server_rights(getuser(), args.server_name, args.base_directory)
        if not owner and os.path.isdir(os.path.join(args.base_directory, mc.DEFAULT_PATHS['servers'], args.server_name)):
            raise OSError("User '%s' does not have rights to %s" % (getuser(),
                                                                    os.path.join(args.base_directory,
                                                                                 args.server_name)))
        else:
            instance = mc(args.server_name, owner, args.base_directory)

        if args.cmd in ['screen', 'console']:
            instance._command_direct('screen -r %s' % instance.screen_pid, instance.env['cwd'])
        elif args.cmd in available_methods:
            retval = getattr(instance, args.cmd)(*arguments)
            if retval:
                if isinstance(retval, types.GeneratorType):
                    pp.pprint(list(retval))
                else:
                    pp.pprint(retval)
            else:
                print '{%s} completed successfully.' % args.cmd
        elif args.cmd in available_properties:
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
            text = '%s %s' % (args.cmd, ' '.join(arguments))
            instance._command_stuff(text)
            print '{%s} sent to gameserver console [screen_pid:%s] successfully.' % (text,
                                                                                     instance.screen_pid)
    else:
        init_args = {
            'server_name': 'throwaway',
            'owner': getuser(),
            'base_directory': args.base_directory
            }

        if args.cmd == 'update_profile':
            try:
                mc(**init_args).update_profile(*arguments)
            except RuntimeWarning as ex:
                print ex.message
        elif args.cmd == 'stock_profile':
            from stock_profiles import STOCK_PROFILES
            profile = iter([i for i in STOCK_PROFILES if i['name'] == arguments[0]]).next()
            mc(**init_args).define_profile(profile)
        elif args.cmd == 'define_profile':
            from collections import OrderedDict
            profile = OrderedDict([(k,None) for k in ('name', 'type', 'url',
                                                      'save_as', 'run_as','ignore')])
            for k,v in profile.iteritems():
                profile[k] = raw_input('%s: ' % k)
            
            mc(**init_args).define_profile(profile)
        elif args.cmd == 'start':
            from procfs_reader import path_owner
            for i in mc.list_servers_start_at_boot(args.base_directory):
                try:
                    owner = path_owner(os.path.join(args.base_directory, mc.DEFAULT_PATHS['servers'], i))
                    print 'starting %s...' % i,
                    mc(i, owner, args.base_directory).start()
                    print ' done'
                except Exception as ex:
                    print ex.message
        elif args.cmd == 'stop':
            from procfs_reader import path_owner
            for i in mc.list_servers_up():
                if os.path.samefile(i.base_dir, args.base_directory):
                    try:
                        srv_ = i.server_name
                        owner = path_owner(os.path.join(i.base_dir, mc.DEFAULT_PATHS['servers'], srv_))
                        print "sending '%s' to %s..." % (args.cmd, srv_),
                        instance = mc(srv_, owner, i.base_dir)._command_stuff(args.cmd)
                        print ' done'
                    except Exception as ex:
                        print ex.message               
        elif args.cmd in ['backup', 'archive']:
            from procfs_reader import path_owner
            for i in mc.list_servers_to_act(args.cmd, args.base_directory):
                try:
                    owner = path_owner(os.path.join(args.base_directory, mc.DEFAULT_PATHS['servers'], i))
                    print 'starting %s for %s...' % (args.cmd, i),
                    getattr(mc, args.cmd)(i, owner, args.base_directory)
                    print ' done'
                except Exception as ex:
                    print ex.message
        elif args.cmd == 'restore':
            from procfs_reader import path_owner
            for i in mc.list_servers_restore_at_boot(args.base_directory):
                try:
                    owner = path_owner(os.path.join(args.base_directory, mc.DEFAULT_PATHS['backup'], i))
                    print 'starting %s for %s...' % (args.cmd, i),
                    mc(i, owner, args.base_directory).restore()
                    print ' done'
                except Exception as ex:
                    print ex.message
        elif args.cmd in available_properties:
            for i in sorted(mc.list_servers(args.base_directory)):
                prop_ = getattr(mc(i, None, args.base_directory), args.cmd)
                print '%s: %s' % (i, prop_) 
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
            
            
