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

def dummy(*args, **kwargs):
    pass

def online_test(original_function):
    global ONLINE_TESTS
    if ONLINE_TESTS:
        return original_function
    else:
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
        self._owner = getpwnam(self._user)
        self._path = self._owner.pw_dir

    def tearDown(self):
        for d in mc.DEFAULT_PATHS.values():
            try:
                rmtree(os.path.join(self._path, d))
            except OSError:
                continue

    def test_bare_environment(self):
        for s in (None, '', False):
            instance = mc()
            self.assertIsNone(instance.server_name)
            with self.assertRaises(AttributeError):
                instance.env

    def test_binary_paths(self):
        instance = mc()
        for k,v in instance.BINARY_PATHS.iteritems():
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
                instance = mc(server_name, self._user)

        for server_name in ok_names:
            instance = mc(server_name, self._user)
            self.assertIsNotNone(instance.server_name)

    def test_set_owner(self):
        with self.assertRaises(KeyError): instance = mc('a', 'fake')
        with self.assertRaises(TypeError): instance = mc('b', 123)
        with self.assertRaises(TypeError): instance = mc('c', {})
        with self.assertRaises(KeyError): instance = mc('d', 'mc', 'fake')
        with self.assertRaises(OSError): instance = mc('e', 'mc', 'www-data')
        with self.assertRaises(KeyError): instance = mc('f', 'will', 'fake')
        with self.assertRaises(OSError): instance = mc('g', 'will', 'www-data')
        with self.assertRaises(KeyError): instance = mc('h', 'fake')
        with self.assertRaises(KeyError): instance = mc('i', 'fake', 'www-data')

    @root_required
    def test_set_owner_two(self):
        #assumes root is part of group GROUP
        from grp import struct_group
        from pwd import struct_passwd

        global GROUP
        
        combinations = [
            ('x', self._user, None),
            ('y', self._user, GROUP),
            ]

        for server_name, user, group in combinations:
            instance = mc(server_name, user, group)
            expected_owner = getpwnam(user)
            expected_group = getgrgid(expected_owner.pw_gid)

            self.assertIsInstance(instance._owner, struct_passwd)
            self.assertIsInstance(instance._group, struct_group)
            
            self.assertEqual(instance._owner, expected_owner)
            self.assertEqual(instance._group, expected_group)
            self.assertTrue(user in expected_group.gr_mem)

    @root_prohibited
    def test_set_owner_three(self):
        #assumes current user is part of group 'group_to_test'
        from grp import struct_group, getgrnam, getgrgid
        from pwd import struct_passwd, getpwnam

        global GROUP
        
        combinations = [
            ('x', self._user, None),
            ('y', self._user, GROUP),
            ]

        for server_name, user, group in combinations:
            instance = mc(server_name, user, group)
            expected_owner = getpwnam(user)
            expected_group = getgrgid(expected_owner.pw_gid)

            self.assertIsInstance(instance._owner, struct_passwd)
            self.assertIsInstance(instance._group, struct_group)
            
            self.assertEqual(instance._owner, expected_owner)
            self.assertEqual(instance._group, expected_group)
            self.assertTrue(user in expected_group.gr_mem)

    def test_load_config(self):
        from conf_reader import config_file
        
        instance = mc('one', self._user)

        self.assertIsInstance(instance.server_properties, config_file)
        self.assertIsInstance(instance.server_properties[:], dict)
        self.assertIsInstance(instance.server_config, config_file)
        self.assertIsInstance(instance.server_config[:], dict)

        self.assertFalse(os.path.isfile(instance.env['sp']))
        self.assertFalse(os.path.isfile(instance.env['sc']))
        
    def test_sp_defaults(self):
        from conf_reader import config_file
        instance = mc('one', self._user)
        instance.create(sp={'server-ip':'127.0.0.1'})
        conf = config_file(instance.env['sp'])
        self.assertFalse(conf._use_sections)
        self.assertEqual(conf['server-ip'],'127.0.0.1')

    def test_sc_defaults(self):
        from conf_reader import config_file
        instance = mc('one', self._user)
        instance.create(sc={'java':{'java-bin':'isworking'}})
        conf = config_file(instance.env['sc'])
        self.assertTrue(conf._use_sections)
        self.assertEqual(conf['java':'java-bin'], 'isworking')

    def test_create(self):
        instance = mc('one', self._user)
        instance.create()

        for d in ('cwd','bwd','awd'):
            self.assertTrue(os.path.exists(instance.env[d]))

        for f in ('sp', 'sc'):
            self.assertTrue(os.path.isfile(instance.env[f]))

        self.assertTrue(instance.server_properties[:])
        self.assertTrue(instance.server_config[:])

        self.assertTrue(instance.command_start)
        self.assertTrue(instance.command_backup)
        self.assertTrue(instance.command_archive)
        self.assertTrue(instance.command_restore)
        with self.assertRaises(RuntimeError):
            self.assertIsNone(instance.command_prune)

        instance = mc('two', self._user)
        instance.create({'java':{'java_xmx':2048}}, {'server-port':'27000'})

        self.assertEqual(instance.server_properties['server-port'], '27000')
        self.assertEqual(instance.server_config['java':'java_xmx'], '2048')

        instance = mc('three', self._user)
        instance.create(sc={'java':{'java_bogus': 'wow!'}}, sp={'bogus-value':'abcd'})

        self.assertEqual(instance.server_properties['bogus-value'], 'abcd')
        self.assertEqual(instance.server_config['java':'java_bogus'], 'wow!')

    def test_change_config(self):
        instance = mc('one', self._user)
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
        instance = mc('one', self._user)
        instance.create()

        self.assertEqual(instance.java_pid, 0)
        self.assertEqual(instance.screen_pid, 0)
        self.assertEqual(instance.memory, '0')

        instance.start()
        time.sleep(1)
        #expected to be zero because no profile/jar
        self.assertEqual(instance.java_pid, 0)
        self.assertEqual(instance.screen_pid, 0)

    def test_archive(self):
        instance = mc('one', self._user)
        instance.create()
        instance.archive()
        self.assertTrue(os.path.isfile(instance._previous_arguments['archive_filename']))

    def test_backup(self):
        instance = mc('one', self._user)
        instance.create()
        instance.backup()
        self.assertTrue(os.path.exists(os.path.join(instance.env['bwd'], 'rdiff-backup-data')))

    def test_restore(self):
        instance = mc('one', self._user)
        instance.create()

        with self.assertRaises(RuntimeError): instance.restore()
        instance.backup()

        rmtree(instance.env['cwd'])
        self.assertFalse(os.path.exists(instance.env['cwd']))
        instance.restore()
        self.assertTrue(os.path.exists(instance.env['cwd']))

        time.sleep(1)
        instance.restore(overwrite=True)

    def test_prune(self):
        instance = mc('one', self._user)
        instance.create()
        instance.backup() #0 incr

        os.remove(instance.env['sp'])

        time.sleep(1)
        instance.backup() #1 incr

        instance._load_config(generate_missing=True)
        time.sleep(1)
        instance.backup() #2 incr

        self.assertEqual(len(instance.list_increments().increments), 2)
        instance.prune(1)
        self.assertEqual(len(instance.list_increments().increments), 1)

        instance.prune('now')
        self.assertEqual(len(instance.list_increments().increments), 0)

    @online_test
    def test_update_file(self):
        instance = mc('one', self._user)
        instance.create()

        url1 = 'http://minecraft.codeemo.com/crux/mineos-scripts/update.sh'
        url2 = 'http://minecraft.codeemo.com/crux/rsync/stable/usr/games/minecraft/mineos.config'
        self.assertTrue(instance._update_file(url1,
                                              instance.env['cwd'],
                                              'update.sh'))
        self.assertTrue(os.path.isfile(os.path.join(instance.env['cwd'],
                                                    'update.sh')))
        self.assertEqual(self.find_owner(os.path.join(instance.env['cwd'],
                                                      'update.sh')), instance._owner.pw_name)
            
        self.assertFalse(instance._update_file(url1,
                                               instance.env['cwd'],
                                               'update.sh'))
        self.assertTrue(instance._update_file(url2,
                                              instance.env['cwd'],
                                              'update.sh'))
        with self.assertRaises(IOError):
            instance._update_file('file',
                                  instance.env['cwd'],
                                  'update.sh')

        with self.assertRaises(IOError):
            instance._update_file('http://fakefilesuffix',
                                  instance.env['cwd'],
                                  'update.sh')

        '''
        the web-ui service run as root will have privileges
        to _update_file to root-owned places.  _update_file
        thus should never ever be executed with unsanitized
        input!
        if self._user != 'root':
            with self.assertRaises(IOError):
                instance._update_file(url1,
                                      '/root',
                                      'update.sh')'''

    def test_copytree(self):
        instance = mc('one', self._user)
        instance.create()

        second_dir = os.path.join(instance._homepath,
                                  instance.DEFAULT_PATHS['servers'],
                                  'two')
        
        instance.copytree(instance.env['cwd'], second_dir)

        for (directory, _, files) in os.walk(instance.env['cwd']):
            for f in files:
                path = os.path.join(second_dir, f)
                self.assertTrue(os.path.exists(path))

        for (directory, _, files) in os.walk(second_dir):
            for f in files:
                path = os.path.join(directory, f)
                self.assertEqual(self.find_owner(path), instance._owner.pw_name)

        self.assertEqual(instance._list_files(instance.env['cwd']),
                         instance._list_files(second_dir))

    def find_owner(self, fn):
        from os import stat
        from pwd import getpwuid

        return getpwuid(stat(fn).st_uid).pw_name

    @online_test
    def test_profiles(self):        
        instance = mc('one', self._user)
        instance.create()

        profile = {
            'name': 'vanilla',
            'type': 'standard_jar',
            'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
            'save_as': 'minecraft_server.jar',
            'run_as': 'minecraft_server.jar',
            'action': 'download',
            'ignore': '',
            }

        self.assertIsNone(instance.profile)
        with self.assertRaises(KeyError): instance.profile = 'vanilla'

        instance.update_profile(profile)
        
        self.assertTrue(os.path.exists(os.path.join(instance.env['pwd'],
                                                    profile['name'])))
        
        self.assertFalse(os.path.isfile(os.path.join(instance.env['pwd'],
                                                     profile['save_as'])))

        self.assertTrue(os.path.isfile(os.path.join(instance.env['pwd'],
                                                    profile['name'],
                                                    profile['run_as'])))

        instance.profile = profile['name']
        self.assertTrue(os.path.isfile(os.path.join(instance.env['cwd'],
                                                    profile['run_as'])))      

        profile['run_as'] = 'minecraft_server.1.6.2.jar'
        
        instance.update_profile(profile, do_download=False)
        
        self.assertEqual(instance.profile_config['vanilla':'run_as'],
                         'minecraft_server.1.6.2.jar')

    @online_test
    def test_start_a_home_server(self):
        instance = mc('one', self._user)
        instance.create()

        profile = {
            'name': 'vanilla',
            'type': 'standard_jar',
            'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
            'save_as': 'minecraft_server.jar',
            'run_as': 'minecraft_server.jar',
            'action': 'download',
            'ignore': '',
            }

        instance.update_profile(profile)
        instance.profile = profile['name']
        instance.start()
        time.sleep(20)
        instance._command_stuff('stop')
        time.sleep(5)
        try:
            instance.kill()
        except RuntimeError:
            pass #just want to suppress, not anticipate
        else:
            time.sleep(3)

    @root_required
    @online_test
    def test_zstart_a_var_games_server(self):

        user_to_use = 'mc'
        group_to_use = 'mcserver'
        base_dir = '/var/games/'
        
        #create first server
        aaaa = mc(server_name='one',
                  owner=user_to_use,
                  group=group_to_use,
                  base_directory=base_dir,
                  container_directory=group_to_use)
        aaaa.create()

        profile = {
            'name': 'vanilla',
            'type': 'standard_jar',
            'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
            'save_as': 'minecraft_server.jar',
            'run_as': 'minecraft_server.jar',
            'action': 'download',
            'ignore': '',
            }

        aaaa.update_profile(profile)
        aaaa.profile = profile['name']
        aaaa.start()
        time.sleep(25)

        #create second server
        bbbb = mc(server_name='two',
                  owner=user_to_use,
                  group=group_to_use,
                  base_directory=base_dir,
                  container_directory=group_to_use)
        bbbb.create(sp={'server-port':25570})
        bbbb.profile = profile['name']
        bbbb.start()
        time.sleep(25)

        #kill servers
        aaaa.kill()
        bbbb.kill()
        time.sleep(10)
        
        with self.assertRaises(RuntimeWarning):
            aaaa.kill()

        with self.assertRaises(RuntimeWarning):
            bbbb.kill()

        rmtree(os.path.join(base_dir, group_to_use))

    
if __name__ == "__main__":
    unittest.main()  

