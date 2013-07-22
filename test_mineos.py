#!/usr/bin/env python2.7

import unittest
import os
import time

from mineos import mc
from shutil import rmtree

class TestMineOS(unittest.TestCase):
    def setUp(self):
        from pwd import getpwnam
        from getpass import getuser
        self._owner = getpwnam(getuser())
        self._path = self._owner.pw_dir

    def tearDown(self):
        for d in ('servers', 'backup', 'archive', 'log'):
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
                instance = mc(server_name)

        for server_name in ok_names:
            instance = mc(server_name)
            self.assertIsNotNone(instance.server_name)

    def test_set_owner(self):
        instance = mc('one')
        
        self.assertTrue(self._owner, instance._owner)

    def test_load_config(self):
        from conf_reader import config_file
        
        instance = mc('one')

        self.assertIsInstance(instance.server_properties, config_file)
        self.assertIsInstance(instance.server_properties[:], dict)
        self.assertIsInstance(instance.server_config, config_file)
        self.assertIsInstance(instance.server_config[:], dict)

        self.assertFalse(os.path.isfile(instance.env['sp']))
        self.assertFalse(os.path.isfile(instance.env['sc']))
        
    def test_create(self):
        instance = mc('one')
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
        self.assertIsNone(instance.command_prune)

        instance = mc('two')
        instance.create({'java':{'java_xmx':2048}}, {'server-port':'27000'})

        self.assertEqual(instance.server_properties['server-port'], '27000')
        self.assertEqual(instance.server_config['java':'java_xmx'], '2048')

        instance = mc('three')
        instance.create({'java':{'java_bogus': 'wow!'}}, {'bogus-value':'abcd'})

        with self.assertRaises(KeyError):
            instance.server_properties['bogus-value']
        with self.assertRaises(KeyError):
            instance.server_config['java':'java_bogus']

    def test_change_config(self):
        instance = mc('one')
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
        instance = mc('one')
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
        instance = mc('one')
        instance.create()
        instance.archive()
        self.assertTrue(os.path.isfile(instance._previous_arguments['archive_filename']))

    def test_backup(self):
        instance = mc('one')
        instance.create()
        instance.backup()
        self.assertTrue(os.path.exists(os.path.join(instance.env['bwd'], 'rdiff-backup-data')))

    def test_restore(self):
        instance = mc('one')
        instance.create()

        with self.assertRaises(RuntimeError): instance.restore()
        instance.backup()

        rmtree(instance.env['cwd'])
        self.assertFalse(os.path.exists(instance.env['cwd']))
        instance.restore()
        self.assertTrue(os.path.exists(instance.env['cwd']))

        time.sleep(1)
        instance.restore(overwrite=True)

    def test_list_increments(self):
        instance = mc('one')
        instance.create()
        self.assertEqual(instance.list_increments().current_mirror, '')
        self.assertEqual(instance.list_increments().increments, [])

        instance.backup()            
        self.assertEqual(len(instance.list_increments().increments), 0)
        self.assertTrue(instance.list_increments().current_mirror)

        time.sleep(1)
        instance.backup()            
        self.assertEqual(len(instance.list_increments().increments), 0)
        self.assertTrue(instance.list_increments().current_mirror)

        os.remove(instance.env['sp'])

        time.sleep(1)
        instance.backup()            
        self.assertEqual(len(instance.list_increments().increments), 1)



if __name__ == "__main__":
    unittest.main()  

