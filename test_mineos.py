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
        self._owner = getpwnam(self._user)
        self._path = '/home/mc'

        self.inst_args = {
            'owner':'mc',
            'base_directory':'/home/mc'
            }

    def tearDown(self):
        for d in mc.DEFAULT_PATHS.values():
            try:
                rmtree(os.path.join(self._path, d))
            except OSError:
                continue

    def test_bare_environment(self):
        for s in (None, '', False):
            with self.assertRaises(TypeError):
                instance = mc()

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
                instance = mc(server_name, **self.inst_args)

        for server_name in ok_names:
            instance = mc(server_name, **self.inst_args)
            self.assertIsNotNone(instance.server_name)

    @skip_test
    @root_prohibited
    def test_create_log(self):
        server_to_create = 'one'
        try:
            logfile = os.path.join(mc().LOGGING_DIR, server_to_create)
            open(logfile, 'a').close()
        except IOError:
            instance = mc(server_to_create)
            instance.create()
            self.assertTrue(os.path.isfile(os.path.join(instance._homepath,
                                                        'log',
                                                        instance.server_name)))
            instance._logger.debug('it works')
        else:
            instance = mc(server_to_create)
            instance.create()
            self.assertTrue(os.path.isfile(os.path.join(instance.LOGGING_DIR,
                                                        'log',
                                                        instance.server_name)))
            instance._logger.debug('it works')

    def test_set_owner(self):
        with self.assertRaises(KeyError): instance = mc('a', owner='fake')
        with self.assertRaises(TypeError): instance = mc('b', owner=123)
        with self.assertRaises(TypeError): instance = mc('c', owner={})
        instance = mc('d', base_directory='/home/mc', owner='mc')
        instance = mc('e', owner='mc')
        instance = mc('f', owner='will')
        instance = mc('g', owner='root')

    def test_load_config(self):
        from conf_reader import config_file
        
        instance = mc('one', **self.inst_args)

        self.assertIsInstance(instance.server_properties, config_file)
        self.assertIsInstance(instance.server_properties[:], dict)
        self.assertIsInstance(instance.server_config, config_file)
        self.assertIsInstance(instance.server_config[:], dict)

        self.assertFalse(os.path.isfile(instance.env['sp']))
        self.assertFalse(os.path.isfile(instance.env['sc']))
        
    def test_sp_defaults(self):
        from conf_reader import config_file
        instance = mc('one', **self.inst_args)
        instance.create(sp={'server-ip':'127.0.0.1'})
        conf = config_file(instance.env['sp'])
        self.assertFalse(conf._use_sections)
        self.assertEqual(conf['server-ip'],'127.0.0.1')

    def test_sc_defaults(self):
        from conf_reader import config_file
        instance = mc('one', **self.inst_args)
        instance.create(sc={'java':{'java-bin':'isworking'}})
        conf = config_file(instance.env['sc'])
        self.assertTrue(conf._use_sections)
        self.assertEqual(conf['java':'java-bin'], 'isworking')

    def test_create(self):
        instance = mc('one', owner='mc', base_directory=self._path)
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

        instance = mc('two', **self.inst_args)
        instance.create({'java':{'java_xmx':2048}}, {'server-port':'27000'})

        self.assertEqual(instance.server_properties['server-port'], '27000')
        self.assertEqual(instance.server_config['java':'java_xmx'], '2048')

        instance = mc('three', **self.inst_args)
        instance.create(sc={'java':{'java_bogus': 'wow!'}}, sp={'bogus-value':'abcd'})

        self.assertEqual(instance.server_properties['bogus-value'], 'abcd')
        self.assertEqual(instance.server_config['java':'java_bogus'], 'wow!')

    def test_change_config(self):
        instance = mc('one', **self.inst_args)
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
        instance = mc('one', **self.inst_args)
        instance.create()

        self.assertIsNone(instance.java_pid)
        self.assertIsNone(instance.screen_pid)
        self.assertEqual(instance.memory, '0')

        instance.start()
        time.sleep(1)
        #expected to be zero because no profile/jar
        self.assertIsNone(instance.java_pid)
        self.assertIsNone(instance.screen_pid)

    def test_archive(self):
        instance = mc('one', **self.inst_args)
        instance.create()
        instance.archive()
        self.assertTrue(os.path.isfile(instance._previous_arguments['archive_filename']))

    def test_backup(self):
        instance = mc('one', **self.inst_args)
        instance.create()
        instance.backup()
        self.assertTrue(os.path.exists(os.path.join(instance.env['bwd'], 'rdiff-backup-data')))

    def test_restore(self):
        instance = mc('one', **self.inst_args)
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
        instance = mc('one', **self.inst_args)
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

    @online_test
    def test_update_file(self):
        instance = mc('one', **self.inst_args)
        instance.create()

        url1 = 'http://minecraft.codeemo.com/crux/mineos-scripts/update.sh'
        url2 = 'http://minecraft.codeemo.com/crux/rsync/stable/usr/games/minecraft/mineos.config'
        self.assertTrue(instance._update_file(url1,
                                              instance.env['cwd'],
                                              'update.sh'))
        self.assertTrue(os.path.isfile(os.path.join(instance.env['cwd'],
                                                    'update.sh')))
        self.assertEqual(self.find_owner(os.path.join(instance.env['cwd'],
                                                      'update.sh')), instance.owner.pw_name)
            
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
        instance = mc('one', **self.inst_args)
        instance.create()

        second_dir = os.path.join(instance.base,
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
                self.assertEqual(self.find_owner(path), instance.owner.pw_name)

        self.assertEqual(mc.list_files(instance.env['cwd']),
                         mc.list_files(second_dir))

    def find_owner(self, fn):
        from os import stat
        from pwd import getpwuid

        return getpwuid(stat(fn).st_uid).pw_name

    @online_test
    def test_profiles(self):        
        instance = mc('one', **self.inst_args)
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
    def test_astart_home_server(self):
        instance = mc('one', **self.inst_args)
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
            time.sleep(1.5)

    @root_required
    @online_test
    def test_zstart_a_var_games_server(self):

        user_to_use = 'mc'
        base_dir = '/var/games/minecraft'

        os.system('mkdir -p %s' % base_dir)
        
        #create first server
        aaaa = mc(server_name='one',
                  owner=user_to_use,
                  base_directory=base_dir)
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
                  base_directory=base_dir)
        bbbb.create(sp={'server-port':25570})
        bbbb.profile = profile['name']
        bbbb.start()
        time.sleep(25)

        #kill servers
        aaaa.kill()
        bbbb.kill()
        time.sleep(5)
        
        with self.assertRaises(RuntimeError):
            aaaa.kill()

        with self.assertRaises(RuntimeError):
            bbbb.kill()

        rmtree(base_dir)

    
if __name__ == "__main__":
    unittest.main()

    '''

    fast = unittest.TestSuite()
    fast.addTest(TestMineOS('test_prune'))
    unittest.TextTestRunner().run(fast)
    '''
    
