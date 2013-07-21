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

    def test_config_file_sectionless_delitem(self):
        directory = os.path.join(self._path, 'log')
        fn = os.path.join(directory,'server.properties')
        os.makedirs(directory)

        conf = config_file(fn)
        conf.use_sections(False)
        self.assertFalse(conf._use_sections)

        del conf['doesnotexist']
        with self.assertRaises(SyntaxError): del conf['doesnotexist':]
        with self.assertRaises(SyntaxError): del conf['doesnotexist'::]
        with self.assertRaises(SyntaxError): del conf['doesnotexist':'stilldoesnt']
        with self.assertRaises(SyntaxError): del conf['doesnotexist':'stilldoesnt':]
        with self.assertRaises(SyntaxError): del conf['doesnotexist':'stilldoesnt':'default']

        with self.assertRaises(TypeError): del conf[5]
        with self.assertRaises(SyntaxError): del conf[5:]
        with self.assertRaises(SyntaxError): del conf[5::]
        with self.assertRaises(SyntaxError): del conf[5:5]
        with self.assertRaises(SyntaxError): del conf[5:5:]
        with self.assertRaises(SyntaxError): del conf[5:5:5]

    def test_config_file_sectionless_getandset(self):
        directory = os.path.join(self._path, 'log')
        fn = os.path.join(directory,'server.properties')
        os.makedirs(directory)

        conf = config_file(fn)
        conf.use_sections(False)
        self.assertFalse(conf._use_sections)

        conf['first'] = 'hello'
        conf['second'] = 150
        conf['third'] = True

        self.assertEqual(conf['first'], 'hello')
        self.assertEqual(conf['second'], '150')
        self.assertEqual(conf['third'], 'True')

        with self.assertRaises(SyntaxError): conf['first':]
        with self.assertRaises(SyntaxError): conf['first'::]
        with self.assertRaises(SyntaxError): conf[::]
        with self.assertRaises(SyntaxError): conf['first':'second']
        with self.assertRaises(SyntaxError): conf['first':'second':]
        with self.assertRaises(SyntaxError): conf['first':'second']
        with self.assertRaises(SyntaxError): conf['first':'second':]
        with self.assertRaises(SyntaxError): conf['first':'second':'third']

        self.assertEqual(conf['doesnotexist'::5], 5)
        self.assertEqual(conf['doesnotexist'::'default'], 'default')

        self.assertIsInstance(conf[:], dict)
        self.assertEqual(conf[:], {
            'first': 'hello',
            'second': '150',
            'third': 'True'
            })

        with self.assertRaises(TypeError): conf[5] = 12
        with self.assertRaises(TypeError): conf[None] = 12
        with self.assertRaises(TypeError): conf[{}] = 12
        with self.assertRaises(TypeError): conf[()] = 12
        with self.assertRaises(KeyError): conf['doesnotexist']

        conf.commit()
        self.assertTrue(os.path.isfile(fn))

        with config_file(fn) as conf:
            pass

    def test_config_file_sections_delitem(self):
        directory = os.path.join(self._path, 'log')
        fn = os.path.join(directory,'server.config')
        os.makedirs(directory)

        conf = config_file(fn)
        self.assertTrue(conf._use_sections)

        with self.assertRaises(SyntaxError): del conf['doesnotexist']
        with self.assertRaises(SyntaxError): del conf['doesnotexist':]
        with self.assertRaises(SyntaxError): del conf['doesnotexist'::]
        with self.assertRaises(KeyError): del conf['doesnotexist':'stilldoesnt']
        with self.assertRaises(KeyError): del conf['doesnotexist':'stilldoesnt':]
        with self.assertRaises(SyntaxError): del conf['doesnotexist':'stilldoesnt':'default']

        with self.assertRaises(SyntaxError): del conf[5]
        with self.assertRaises(TypeError): del conf[5:]
        with self.assertRaises(SyntaxError): del conf[5::]
        with self.assertRaises(TypeError): del conf[5:5]
        with self.assertRaises(TypeError): del conf[5:5:]
        with self.assertRaises(SyntaxError): del conf[5:5:5]

    def test_config_file_sections_getandset(self):
        directory = os.path.join(self._path, 'log')
        fn = os.path.join(directory,'server.config')
        os.makedirs(directory)

        conf = config_file(fn)
        self.assertTrue(conf._use_sections)

        with self.assertRaises(SyntaxError): conf['section'] = 'hello'
        with self.assertRaises(SyntaxError): conf['section':] = 'hello'
        with self.assertRaises(SyntaxError): conf['section'::] = 'hello'
        with self.assertRaises(KeyError): conf['section':'option'] = 'hello'
        with self.assertRaises(KeyError): conf['section':'option':] = 'hello'
        with self.assertRaises(SyntaxError): conf[:] = 'hello'
        with self.assertRaises(SyntaxError): conf[::] = 'hello'

        with self.assertRaises(TypeError): conf[5:] = 'hello'
        with self.assertRaises(TypeError): conf[5:5] = 'hello'
        with self.assertRaises(SyntaxError): conf[5:5:5] = 'hello'
        with self.assertRaises(TypeError): conf['5':5] = 'hello'
        with self.assertRaises(TypeError): conf[5:'5'] = 'hello'
        with self.assertRaises(SyntaxError): conf[5:'5':5] = 'hello'

        self.assertIsInstance(conf[:], dict)

        conf.add_section('java')
        conf['java':'java_xmx'] = 512
        conf['java':'java_xms'] = '256'
        conf['java':'thirdcolon':] = 'present'

        self.assertIsInstance(conf[:], dict)
        self.assertEqual(conf[:], {
            'java': {
                'java_xmx': '512',
                'java_xms': '256',
                'thirdcolon': 'present'
                }
            })

        self.assertIsInstance(conf['java'], dict)
        self.assertEqual(conf['java'], {
                'java_xmx': '512',
                'java_xms': '256',
                'thirdcolon': 'present'
                })

        self.assertEqual(conf['java':], {
                'java_xmx': '512',
                'java_xms': '256',
                'thirdcolon': 'present'
                })

        self.assertEqual(conf['java':'java_xmx'], '512')
        self.assertEqual(conf['java':'java_xms'], '256')

        self.assertEqual(conf['java':'madeup':768], 768)
        self.assertEqual(conf['java':'fake':'attr'], 'attr')

        with self.assertRaises(SyntaxError): conf['java':] = 'hello'
        with self.assertRaises(SyntaxError): conf['java'::] = 'hello'
        with self.assertRaises(SyntaxError): conf[::] = 'hello'
        with self.assertRaises(SyntaxError): conf['java':'second':'third'] = 'hello'

        with self.assertRaises(SyntaxError): conf[5] = 12
        with self.assertRaises(SyntaxError): conf[None] = 12
        with self.assertRaises(SyntaxError): conf[{}] = 12
        with self.assertRaises(SyntaxError): conf[()] = 12

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
