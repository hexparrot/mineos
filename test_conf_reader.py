#!/usr/bin/env python2.7

import unittest
import os

from conf_reader import config_file

class TestConfigFile(unittest.TestCase):
    CONFIG_FILES = {
        'sections': 'cfg_sections',
        'sectionless': 'cfg_sectionless'
        }
    
    def setUp(self):
        pass

    def tearDown(self):
        for v in self.CONFIG_FILES.values():
            try:
                os.remove(v)
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
        conf = config_file(self.CONFIG_FILES['sectionless'])
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
        conf = config_file(self.CONFIG_FILES['sectionless'])
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
        self.assertTrue(os.path.isfile(self.CONFIG_FILES['sectionless']))

        with config_file(self.CONFIG_FILES['sectionless']) as conf:
            pass

    def test_config_file_sections_delitem(self):
        conf = config_file(self.CONFIG_FILES['sections'])
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
        conf = config_file(self.CONFIG_FILES['sections'])
        self.assertTrue(conf._use_sections)

        with self.assertRaises(SyntaxError): conf['section'] = 'hello'
        with self.assertRaises(TypeError): conf['section':] = 'hello'
        with self.assertRaises(TypeError): conf['section'::] = 'hello'
        with self.assertRaises(KeyError): conf['section':'option'] = 'hello'
        with self.assertRaises(KeyError): conf['section':'option':] = 'hello'
        with self.assertRaises(TypeError): conf[:] = 'hello'
        with self.assertRaises(TypeError): conf[::] = 'hello'

        with self.assertRaises(TypeError): conf[5:] = 'hello'
        with self.assertRaises(TypeError): conf[5:5] = 'hello'
        with self.assertRaises(SyntaxError): conf[5:5:5] = 'hello'
        with self.assertRaises(TypeError): conf['5':5] = 'hello'
        with self.assertRaises(TypeError): conf[5:'5'] = 'hello'
        with self.assertRaises(SyntaxError): conf[5:'5':5] = 'hello'

        with self.assertRaises(KeyError): conf['fakesection']
        with self.assertRaises(KeyError): conf['fakesection':]
        with self.assertRaises(KeyError): conf['fakesection'::]
        with self.assertRaises(KeyError): conf['fakesection':'fake']
        with self.assertRaises(KeyError): conf['fakesection':'fake':]

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

        with self.assertRaises(TypeError): conf['java':] = 'hello'
        with self.assertRaises(TypeError): conf['java'::] = 'hello'
        with self.assertRaises(TypeError): conf[::] = 'hello'
        with self.assertRaises(SyntaxError): conf['java':'second':'third'] = 'hello'

        self.assertIsNone(conf['java':'madeup'])
        self.assertIsNone(conf['java':'madeup':])

        with self.assertRaises(SyntaxError): conf[5] = 12
        with self.assertRaises(SyntaxError): conf[None] = 12
        with self.assertRaises(SyntaxError): conf[{}] = 12
        with self.assertRaises(SyntaxError): conf[()] = 12

        conf.commit()
        self.assertTrue(os.path.isfile(self.CONFIG_FILES['sections']))

        with config_file(self.CONFIG_FILES['sections']) as conf:
            pass

if __name__ == "__main__":
    unittest.main()  
