#!/usr/bin/env python2.7

import unittest
import os

from conf_reader import config_file
from mineos import mc
from shutil import rmtree

class TestMineOS(unittest.TestCase):
    def setUp(self):
        from pwd import getpwnam
        from getpass import getuser
        self._path = getpwnam(getuser()).pw_dir

    def tearDown(self):
        for d in ('servers', 'backup', 'archive', 'log'):
            try:
                rmtree(os.path.join(self._path, d))
            except OSError:
                continue

    def test_config_file(self):
        conf = config_file()
        self.assertIsInstance(conf[:], dict)
        self.assertFalse(conf[:])
        self.assertTrue(conf._use_sections)

        conf.use_sections(False)
        self.assertFalse(conf._use_sections)

        with self.assertRaises(TypeError):
            conf.commit()

    def test_config_file_create_sectionless(self):
        directory = os.path.join(self._path, 'log')
        fn = os.path.join(directory,'server.properties')
        os.makedirs(directory)

        conf = config_file(fn)
        self.assertTrue(conf._use_sections)
        conf.use_sections(False)
        self.assertFalse(conf._use_sections)
        
        conf['first'] = 'hello'
        self.assertEqual(conf['first'], 'hello')
        self.assertEqual(conf[:], {'first':'hello'})

        with self.assertRaises(SyntaxError):
            self.assertEqual(conf['first':], 'hello')

        conf['first'] = 'goodbye'
        self.assertEqual(conf['first'], 'goodbye')
        self.assertEqual(conf[:], {'first':'goodbye'})

        with self.assertRaises(SyntaxError):
            self.assertEqual(conf['first':], 'goodbye')

        conf['second'] = 'yes'
        self.assertEqual(conf[:], {
            'first':'goodbye',
            'second':'yes'})

        with self.assertRaises(TypeError):
            conf[5] = 12

        conf['5'] = 12
        self.assertEqual(conf['5'], '12')        

        with self.assertRaises(TypeError):
            self.assertEqual(conf[5], '12')

        with self.assertRaises(KeyError):
            conf['third']

        with self.assertRaises(SyntaxError):
            conf['section':'option']

        with self.assertRaises(SyntaxError):
            conf['option':] = 5

        with self.assertRaises(SyntaxError):
            conf['option':] = 5

        self.assertEqual(conf['aaa'::5], 5)
        self.assertEqual(conf['hello'::5], 5)

        conf['throwaway'] = 'me'

        with self.assertRaises(SyntaxError):
            del conf['throwaway':]

        with self.assertRaises(TypeError):
            del conf[5]

        with self.assertRaises(SyntaxError):
            del conf['throwaway':'me']

        del conf['throwaway']
        del conf['111']
        del conf['makebelieve']

        conf.commit()
        self.assertTrue(os.path.isfile(fn))

        with config_file(fn) as conf:
            pass

    def test_config_file_create_sections(self):
        directory = os.path.join(self._path, 'log')
        fn = os.path.join(directory,'server.config')
        os.makedirs(directory)

        conf = config_file(fn)
        self.assertTrue(conf._use_sections)

        with self.assertRaises(KeyError):
            conf['java':'java_xmx'] = '256'

        with self.assertRaises(KeyError):
            conf['java':'java_xmx']

        conf.add_section('java')
        conf['java':'java_xmx'] = '256'
        self.assertEquals(conf['java':'java_xmx'], '256')
        self.assertEquals(conf['java':], {'java_xmx':'256'})
        self.assertEquals(conf[:], {
            'java': {
                'java_xmx': '256',
                }
            })

        conf['java':'java_xmx'] = '512'
        self.assertEquals(conf['java':'java_xmx'], '512')
        self.assertEquals(conf['java':'java_path':'/usr/bin/java'], '/usr/bin/java')
        self.assertEquals(conf['java':'java_xms': 512], 512)

        conf.add_section('5')
        conf['5':'word'] = 'bird'

        with self.assertRaises(TypeError):
            self.assertEquals(conf[5:'word'], 'bird')

        with self.assertRaises(TypeError):
            conf['5':10] = 'amiss'
            
        with self.assertRaises(TypeError):
            conf[5:10]

        with self.assertRaises(TypeError):
            conf['5':10]

        with self.assertRaises(TypeError):
            self.assertEquals(conf[5:15:20], 20)

        with self.assertRaises(KeyError):
            conf['s':'o'] = 'var'

        conf.add_section('s')
        conf['s':'o'] = 'var'

        with self.assertRaises(SyntaxError):
            del conf[5]

        with self.assertRaises(SyntaxError):
            del conf['aaaaa']

        with self.assertRaises(SyntaxError):
            del conf['s':]

        del conf['s':'zzz']
        del conf['s':'o']

        conf.commit()
        self.assertTrue(os.path.isfile(fn))

        with config_file(fn) as conf:
            pass
  
    def test_bare_environment(self):
        for s in (None, '', False):
            instance = mc()
            self.assertIsNone(instance.server_name)
            with self.assertRaises(AttributeError):
                instance.env

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

if __name__ == "__main__":
    unittest.main()  
