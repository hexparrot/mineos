#!/usr/bin/env python2.7
"""
    Subclass of Configparser for sectionless configuration files.
    Implements slicing as additional get/set methods.
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import unittest
from config_fs import ConfigFS

class TestConfigFS(unittest.TestCase):
    def setUp(self):
        self.instance = ConfigFS()

    def tearDown(self):
        pass

    def test_load_yaml(self):
        fn = '/root/bukkit.yml'
        data = ConfigFS.load('yaml', fn)
        self.assertIsInstance(data, dict)
        self.assertTrue(data)

    def test_load_sections(self):
        fn = '/root/server.config'
        data = ConfigFS.load('sections', fn)
        self.assertIsInstance(data, dict)
        self.assertTrue(data)

    def test_load_sectionless(self):
        fn = '/root/server.properties'
        data = ConfigFS.load('sectionless', fn)
        self.assertIsInstance(data, dict)
        self.assertTrue(data)

    def test_load_flat(self):
        fn = '/root/resolv.conf'
        data = ConfigFS.load('flat', fn)
        self.assertIsInstance(data, list)
        self.assertTrue(data)

    def test_load_fakefile(self):
        for i in ['yaml', 'flat', 'sections', 'sectionless']:
            with self.assertRaises(IOError) as e:
                ConfigFS.load(i, '/root/fakefile')

    def test_mount(self):
        from fuse import Stat
        
        fn = '/root/bukkit.yml'
        dest = '/servers/a/bukkit.yml'
        self.instance.mount('yaml', fn, dest)
        self.assertIsInstance(self.instance.data(dest), dict)
        self.assertTrue(self.instance.data(dest))
        self.assertIsInstance(self.instance.stat(dest), Stat)
        self.assertTrue(self.instance.stat(dest))

    def test_load_unmounted(self):
        dest = '/servers/a/bukkit.yml'
        with self.assertRaises(KeyError) as e:
            self.assertTrue(self.instance.data(dest))

    def test_reload_mounted(self):
        def touch(fname, times=None):
            import os
            with open(fname, 'a'):
                os.utime(fname, times)
            
        fn = '/root/bukkit.yml'
        dest = '/servers/a/bukkit.yml'
        self.instance.mount('yaml', fn, dest)

        data = self.instance.data(dest)
        self.assertTrue(data)
        
        self.assertEquals(self.instance.data(dest), data)
        touch(fn)
        self.assertEquals(self.instance.data(dest), data)

    def test_list_dirs_sections(self):
        fn = '/root/server.config'
        dest = '/servers/a/server.config'
        self.instance.mount('sections', fn, dest)

        dirs = set(self.instance.list_dirs(dest))
        expected = set(['crontabs','java','minecraft','onreboot'])
        self.assertSetEqual(dirs, expected)

    def test_list_files_sections(self):
        fn = '/root/server.config'
        dest = '/servers/a/server.config'
        self.instance.mount('sections', fn, dest)

        dirs = set(self.instance.list_files(dest, 'onreboot'))
        expected = set(['restore', 'start'])
        self.assertSetEqual(dirs, expected)

    def test_list_dirs_yaml(self):
        fn = '/root/bukkit.yml'
        dest = '/servers/a/bukkit.yml'
        self.instance.mount('yaml', fn, dest)

        dirs = set(self.instance.list_dirs(dest))
        expected = set(['settings','spawn-limits','chunk-gc',
                        'ticks-per','auto-updater','database'])
        self.assertSetEqual(dirs, expected)

    def test_list_files_yaml(self):
        #incomplete due to recursion
        fn = '/root/bukkit.yml'
        dest = '/servers/a/bukkit.yml'
        self.instance.mount('yaml', fn, dest)

        dirs = set(self.instance.list_files(dest, 'ticks-per'))
        expected = set(['animal-spawns','monster-spawns','autosave'])
        self.assertSetEqual(dirs, expected)
        
    def test_list_files_sectionless(self):
        fn = '/root/server.properties'
        dest = '/servers/a/server.properties'
        self.instance.mount('sectionless', fn, dest)

        dirs = set(self.instance.list_files(dest))
        expected = set(['level-name','server-ip','motd','max-players'])
        self.assertFalse([e for e in expected if e not in dirs])

    def test_list_files_flat(self):
        fn = '/root/resolv.conf'
        dest = '/servers/a/resolv.conf'
        self.instance.mount('flat', fn, dest)

        dirs = set(self.instance.list_files(dest))
        expected = set(['nameserver 140.198.100.207'])
        self.assertFalse([e for e in expected if e not in dirs])

    def test_contents_sections(self):
        fn = '/root/server.config'
        dest = '/servers/a/server.config'
        self.instance.mount('sections', fn, dest)

        self.assertEquals(self.instance.contents(dest, 'java_xmx', 'java'),
                          '256\n')

    def test_contents_sectionless(self):
        fn = '/root/server.properties'
        dest = '/servers/a/server.properties'
        self.instance.mount('sectionless', fn, dest)

        self.assertEquals(self.instance.contents(dest, 'server-ip'),
                          '0.0.0.0\n')

    def test_contents_flat(self):
        fn = '/root/resolv.conf'
        dest = '/servers/a/resolv.conf'
        self.instance.mount('flat', fn, dest)

        self.assertEquals(self.instance.contents(dest, 2),
                          'nameserver 140.198.100.207\n')

    def test_contents_yaml(self):
        #incomplete due to recursion
        fn = '/root/bukkit.yml'
        dest = '/servers/a/bukkit.yml'
        self.instance.mount('yaml', fn, dest)

        self.assertEquals(self.instance.contents(dest, 'driver', 'database'),
                          'org.sqlite.JDBC\n')

    def test_stat_as_directory(self):
        from fuse import Stat
        from stat import S_IFDIR
        
        fn = '/root/server.properties'
        dest = '/servers/a/server.properties'
        self.instance.mount('sectionless', fn, dest)

        stat_result = self.instance.stat_as_directory(dest)
        self.assertIsInstance(stat_result, Stat)
        self.assertEquals(stat_result.st_nlink, 2)
        self.assertEquals(stat_result.st_size, 4096)
        self.assertEquals(stat_result.st_mode, S_IFDIR | 0555)

    def test_stat_for_config(self):
        from fuse import Stat
        from stat import S_IFREG

        fn = '/root/server.properties'
        dest = '/servers/a/server.properties'
        self.instance.mount('sectionless', fn, dest)

        stat_result = self.instance.stat_for_config(dest)
        self.assertIsInstance(stat_result, Stat)
        self.assertEquals(stat_result.st_nlink, 1)
        self.assertEquals(stat_result.st_mode, S_IFREG | 0664)

        

if __name__ == "__main__":
    unittest.main()  
