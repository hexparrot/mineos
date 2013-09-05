#!/usr/bin/env python2.7

import unittest
import os
import time

from mineos import mc
from shutil import rmtree
from getpass import getuser

from pwd import getpwnam
from grp import getgrgid

USER = getuser()
GROUP = getgrgid(getpwnam(USER).pw_gid).gr_name
ONLINE_TESTS = True

VANILLA_PROFILE = {
    'name': 'vanilla',
    'type': 'standard_jar',
    'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
    'save_as': 'minecraft_server.jar',
    'run_as': 'minecraft_server.jar',
    'action': 'download',
    'ignore': '',
    }

def dummy(*args, **kwargs):
    pass

def online_test(original_function):
    global ONLINE_TESTS
    if ONLINE_TESTS:
        return original_function
    else:
        return dummy

def skip_test(original_function):
    def dummy(*args, **kwargs):
        pass
    return dummy

def root_required(original_function):
    global USER
    if USER == 'root':
        return original_function
    else:
        return dummy

def root_prohibited(original_function):
    global USER
    if USER != 'root':
        return original_function
    else:
        return dummy

class TestMineOS(unittest.TestCase):
    def setUp(self):
        global USER
        self._user = USER

        self.args = {
            'root': {
                'owner': 'root',
                'base_directory': '/root'
                },
            'mc': {
                'owner': 'mc',
                'base_directory': '/home/mc'
                }
            }

        self.args['self'] =  {
            'owner': getpwnam(USER).pw_name,
            'base_directory': getpwnam(USER).pw_dir
            }

        try:
            self.instance_arguments = self.args.get(USER)
        except KeyError:
            self.instance_arguments = self.args['self']

    def tearDown(self):
        for d in mc.DEFAULT_PATHS.values():
            try:
                rmtree(os.path.join(self.args[self._user]['base_directory'], d))
            except OSError:
                continue

    def test_bare_environment(self):
        with self.assertRaises(TypeError): instance = mc()
            
        for s in (False,):
            with self.assertRaises(ValueError): instance = mc(s)

    def test_binary_paths(self):
        for k,v in mc.BINARY_PATHS.iteritems():
            self.assertIsInstance(v, str)
            self.assertTrue(v)

    def test_valid_server_name(self):
        bad_names = ['this!', 'another,server', '"hello"',
                     '.minecraft', 'top^sirloin', 'me@you',
                     'server-with-hyphens','`', '\t',
                     'minecraft 1.6', '']

        ok_names = ['server', 'pvp', '21324', 'server_one',
                    'minecraft1.6', '_a_server']

        for server_name in bad_names:
            with self.assertRaises(ValueError):
                instance = mc(server_name, **self.instance_arguments)

        for server_name in ok_names:
            instance = mc(server_name, **self.instance_arguments)
            self.assertIsNotNone(instance.server_name)

    def test_set_owner(self):
        mc('a', owner='fake')
        mc('b', owner=123)
        mc('c', owner={})
        mc('d', owner='mc', base_directory='/home/mc')
        mc('e', owner='mc', base_directory='/var/games/minecraft')
        mc('f', owner='mc')
        mc('g', owner='root')
        mc('h', owner='root', base_directory='/home/mc')
        mc('i', owner='root', base_directory='/var/games/minecraft')

    def test_load_config(self):
        from conf_reader import config_file
        
        instance = mc('one', **self.instance_arguments)

        self.assertIsInstance(instance.server_properties, config_file)
        self.assertIsInstance(instance.server_properties[:], dict)
        self.assertIsInstance(instance.server_config, config_file)
        self.assertIsInstance(instance.server_config[:], dict)
        self.assertIsInstance(instance.profile_config, config_file)
        self.assertIsInstance(instance.profile_config[:], dict)

        self.assertFalse(os.path.isfile(instance.env['sp']))
        self.assertFalse(os.path.isfile(instance.env['sc']))
        self.assertFalse(os.path.isfile(instance.env['pc']))
        
    def test_sp_defaults(self):
        from conf_reader import config_file
        instance = mc('one', **self.instance_arguments)
        instance.create(sp={'server-ip':'127.0.0.1'})
        
        conf = config_file(instance.env['sp'])
        self.assertFalse(conf._use_sections)
        self.assertEqual(conf['server-ip'],'127.0.0.1')
        
        instance = mc('one', **self.instance_arguments)
        self.assertFalse(conf._use_sections)
        self.assertEqual(instance.server_properties['server-ip'], '127.0.0.1')

    def test_sc_defaults(self):
        from conf_reader import config_file
        instance = mc('one', **self.instance_arguments)
        instance.create(sc={'java':{'java-bin':'isworking'}})
        
        conf = config_file(instance.env['sc'])
        self.assertTrue(conf._use_sections)
        self.assertEqual(conf['java':'java-bin'], 'isworking')

        instance = mc('one', **self.instance_arguments)
        self.assertTrue(conf._use_sections)
        self.assertEqual(instance.server_config['java':'java-bin'], 'isworking')

    def test_create(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()

        for d in ('cwd','bwd','awd'):
            self.assertTrue(os.path.exists(instance.env[d]))

        for f in ('sp', 'sc'):
            self.assertTrue(os.path.isfile(instance.env[f]))

        self.assertTrue(instance.server_properties[:])
        self.assertTrue(instance.server_config[:])

        with self.assertRaises(RuntimeError):
            self.assertTrue(instance.command_start)
        with self.assertRaises(RuntimeError):
            self.assertIsNone(instance.command_kill)
            
        self.assertTrue(instance.command_backup)
        self.assertTrue(instance.command_archive)
        self.assertTrue(instance.command_restore)

        ''' FIXME: how should prune/apply_profile/wget_profile respond? '''

        instance = mc('two', **self.instance_arguments)
        instance.create({'java':{'java_xmx':2048}}, {'server-port':'27000'})

        self.assertEqual(instance.server_properties['server-port'], '27000')
        self.assertEqual(instance.server_config['java':'java_xmx'], '2048')

        instance = mc('three', **self.instance_arguments)
        instance.create(sc={'java':{'java_bogus': 'wow!'}}, sp={'bogus-value':'abcd'})

        self.assertEqual(instance.server_properties['bogus-value'], 'abcd')
        self.assertEqual(instance.server_config['java':'java_bogus'], 'wow!')

    def test_change_config(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()

        with instance.server_properties as sp:
            sp['server-ip'] = '127.0.0.1'

        self.assertEqual(instance.server_properties['server-ip'], '127.0.0.1')
        instance._load_config()
        self.assertEqual(instance.server_properties['server-ip'], '127.0.0.1')

        with instance.server_config as sc:
            sc['java':'java_xmx'] = '1024'

        self.assertEqual(instance.server_config['java':'java_xmx'], '1024')
        instance._load_config()
        self.assertEqual(instance.server_config['java':'java_xmx'], '1024')

    def test_start(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()

        self.assertIsNone(instance.java_pid)
        self.assertIsNone(instance.screen_pid)
        self.assertEqual(instance.memory, '0')

        with self.assertRaises(RuntimeError):
            instance.start()

        self.assertIsNone(instance.java_pid)
        self.assertIsNone(instance.screen_pid)

    def test_archive(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()
        instance.archive()
        self.assertTrue(os.path.isfile(instance._previous_arguments['archive_filename']))

    def test_backup(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()
        instance.backup()
        self.assertTrue(os.path.exists(os.path.join(instance.env['bwd'], 'rdiff-backup-data')))

    def test_restore(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()

        with self.assertRaises(RuntimeError): instance.restore()

        instance.backup()
        rmtree(instance.env['cwd'])
        
        self.assertFalse(os.path.exists(instance.env['cwd']))
        instance.restore()
        self.assertTrue(os.path.exists(instance.env['cwd']))

        time.sleep(1)
        instance.restore(force=True)

    def test_prune(self):
        instance = mc('one', **self.instance_arguments)
        instance.create()

        for d in ('cwd','bwd','awd'):
            self.assertTrue(os.path.exists(instance.env[d]))

        instance.backup() #0 incr
        self.assertEqual(len(instance.list_increments().increments), 0)

        instance._command_direct('touch me', instance.env['cwd'])
        self.assertTrue(os.path.isfile(os.path.join(instance.env['cwd'], 'me')))

        time.sleep(1.1)
        instance.backup() #1 incr
        self.assertEqual(len(instance.list_increments().increments), 1)

        instance._command_direct('touch you', instance.env['cwd'])
        self.assertTrue(os.path.isfile(os.path.join(instance.env['cwd'], 'you')))
        
        time.sleep(1.2)
        instance.backup() #2 incr

        self.assertEqual(len(instance.list_increments().increments), 2)
        instance.prune(1)
        self.assertEqual(len(instance.list_increments().increments), 1)

        instance.prune('now')
        self.assertEqual(len(instance.list_increments().increments), 0)

    def find_owner(self, fn):
        from os import stat
        from pwd import getpwuid

        return getpwuid(stat(fn).st_uid).pw_name

    @online_test
    def test_profiles(self):
        global VANILLA_PROFILE

        mc._make_skeleton(self.instance_arguments['base_directory'])
        instance = mc('one', **self.instance_arguments)
        instance.create()

        self.assertIsNone(instance.profile)
        with self.assertRaises(KeyError): instance.profile = 'vanilla'

        instance.define_profile(VANILLA_PROFILE)
        instance.update_profile(VANILLA_PROFILE['name'])
        
        self.assertTrue(os.path.exists(os.path.join(instance.env['pwd'],
                                                    VANILLA_PROFILE['name'])))
        
        self.assertFalse(os.path.isfile(os.path.join(instance.env['pwd'],
                                                     VANILLA_PROFILE['save_as'])))

        self.assertTrue(os.path.isfile(os.path.join(instance.env['pwd'],
                                                    VANILLA_PROFILE['name'],
                                                    VANILLA_PROFILE['run_as'])))

        from copy import copy
        newprofile = copy(VANILLA_PROFILE)
        newprofile['run_as'] = 'minecraft_server.1.6.2.jar'
        
        instance.define_profile(newprofile)
        
        self.assertEqual(instance.profile_config['vanilla':'run_as'],
                         'minecraft_server.1.6.2.jar')

    @online_test
    def test_update_profile(self):
        global VANILLA_PROFILE

        mc._make_skeleton(self.instance_arguments['base_directory'])
        instance = mc('one', **self.instance_arguments)
        instance.define_profile(VANILLA_PROFILE)

        with self.assertRaises(RuntimeError):
            instance.update_profile(VANILLA_PROFILE['name'], 'asdfasdf')
            
        instance.update_profile(VANILLA_PROFILE['name'])

        with self.assertRaises(RuntimeWarning):
            instance.update_profile(VANILLA_PROFILE['name'], '39df9f29e6904ea7b351ffb4fe949881')

        with self.assertRaises(RuntimeWarning):
            instance.update_profile(VANILLA_PROFILE['name'])

    @online_test
    def test_profile_jar_match_md5(self):
        global VANILLA_PROFILE

        mc._make_skeleton(self.instance_arguments['base_directory'])
        instance = mc('one', **self.instance_arguments)
        instance.create()
        
        instance.define_profile(VANILLA_PROFILE)
        instance.update_profile(VANILLA_PROFILE['name'])
        instance.profile = VANILLA_PROFILE['name']

        with instance.profile_config as pc:
            pc[VANILLA_PROFILE['name']:'run_as_md5'] = 'abcd'

        self.assertEqual(instance.profile_config[VANILLA_PROFILE['name']:'run_as_md5'], 'abcd')

    @online_test
    def test_start_home_server(self):
        global VANILLA_PROFILE

        mc._make_skeleton(self.instance_arguments['base_directory'])
        instance = mc('one', **self.instance_arguments)
        instance.create()

        instance.define_profile(VANILLA_PROFILE)
        instance.update_profile(VANILLA_PROFILE['name'])
        instance.profile = VANILLA_PROFILE['name']
        instance.start()
        time.sleep(20)
        self.assertTrue(instance.up)
        instance._command_stuff('stop')
        time.sleep(5)
        try:
            instance.kill()
        except RuntimeError:
            pass #just want to suppress, not anticipate
        else:
            time.sleep(1.5)

    @online_test
    @skip_test
    def test_start_home_server_x2(self):
        global VANILLA_PROFILE
        ta = mc('throwaway', **self.instance_arguments)
        ta.define_profile(VANILLA_PROFILE)
        ta.update_profile(VANILLA_PROFILE['name'])
        
        srv_a = mc('one', **self.instance_arguments)
        srv_a.create(sp={'server-port':25566})
        srv_a.profile = VANILLA_PROFILE['name']

        srv_b = mc('two', **self.instance_arguments)
        srv_b.create(sp={'server-port':25567})
        srv_b.profile = VANILLA_PROFILE['name']
        
        srv_a.start()
        time.sleep(20)
        self.assertTrue(srv_a.up)

        srv_b.start()
        time.sleep(20)
        self.assertTrue(srv_b.up)

        srv_a._command_stuff('stop')
        srv_b._command_stuff('stop')

        time.sleep(5)
        
        try:
            srv_a.kill()
        except RuntimeError:
            pass #just want to suppress, not anticipate
        try:
            srv_b.kill()
        except RuntimeError:
            pass #just want to suppress, not anticipate

        time.sleep(1.5)

    
if __name__ == "__main__":
    unittest.main()

    '''

    fast = unittest.TestSuite()
    fast.addTest(TestMineOS('test_prune'))
    unittest.TextTestRunner().run(fast)
    '''
    
