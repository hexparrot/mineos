#!/usr/bin/env python

import unittest, os, fuse, subprocess, errno
from functools import partial
from mineos import mc
from time import sleep

fuse.fuse_python_api = (0, 2)

MINEOS_SKELETON = '/var/games/minecraft'
MOUNT_POINT = '/tmp/fs'
UNPRIVILEGED_USER = 'mc'
REAL_SERVER = 'a'

class TestFuseFS(unittest.TestCase):   
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def system(self, command):
        os.system(command)

    def call(self, command):
        from shlex import split

        with open('/dev/null', 'w') as nulldev:
            subprocess.check_call(split(command),
                                  stderr=nulldev,
                                  stdout=nulldev)

    def join(self, *paths):
        return os.path.join(MOUNT_POINT, *paths)

    def test_external_setup(self):
        self.assertTrue(os.path.exists(MOUNT_POINT))

    def test_root_dir(self):
        for d in ['profiles', 'servers']:
            self.assertTrue(os.path.isdir(os.path.join(MOUNT_POINT,d)))

    def test_server_dir(self):
        for s in next(os.walk(self.join('servers')))[1]:
            for d in ['server.properties', 'server.config',
                      'banned-ips', 'banned-players',
                      'white-list']:
                self.assertTrue(os.path.isdir(self.join('servers', s, d)))

    def test_regular_files(self):
        for s in next(os.walk(self.join('servers')))[1]:
            for d in ['server.properties',
                      'banned-ips', 'banned-players',
                      'white-list']:
                prefix_path = self.join('servers',s,d)
                for f in os.listdir(prefix_path):
                    self.assertTrue(os.path.isfile(os.path.join(prefix_path, f)))

            prefix_path = self.join('servers', s, 'server.config')
            for d in os.listdir(prefix_path):
                full_path = os.path.join(prefix_path, d)
                self.assertTrue(os.path.isdir(full_path))
                for f in os.listdir(full_path):
                    self.assertTrue(os.path.isfile(os.path.join(full_path, f)))
                         
    def test_ls_fake_dir(self):
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('fakedir'))
            self.assertEqual(e.returncode, errno.ENOENT)
                 
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('servers/fakeserver'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('servers/fakeserver/server.config'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('servers/fakeserver/server.config/java'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('servers/fakeserver/server.config/javac'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('profiles/fakeprofile'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % self.join('servers/%s/server.config/javac' % REAL_SERVER))
            self.assertEqual(e.returncode, errno.ENOENT)

    def test_cd_fake_dir(self):
        with self.assertRaises(OSError) as e:
            self.call('cd %s' % self.join('fakeo'))
            self.assertEqual(e.returncode, errno.ENOENT)
            
        with self.assertRaises(OSError) as e:
            self.call('cd %s' % self.join('servers/fake'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % self.join('servers/fake/server.config'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % self.join('servers/fake/server.config/java'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % self.join('servers/fake/server.properties/javac'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % self.join('servers/%s/server.config/fake' % REAL_SERVER))
            self.assertEqual(e.returncode, errno.ENOENT)

    def test_create_server_property(self):
        fn = self.join('servers/%s/server.properties/newprop' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.system('echo 5 >> %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '5\n')

    def test_create_server_config(self):
        fn = self.join('servers/%s/server.config/java/java_fake' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.system('echo 256 >> %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '256\n')

    def test_create_server_config_section(self):
        #this is failing, but is undetected because of system
        fn = self.join('servers/%s/server.config/newsect' % REAL_SERVER)
        self.system('mkdir %s' % fn)
        self.assertTrue(os.path.isdir(fn))

    def test_delete_server_property(self):
        fn = self.join('servers/%s/server.properties/newprop2' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        self.system('rm %s' % fn)
        self.assertFalse(os.path.isfile(fn))

    def test_delete_server_config(self):
        fn = self.join('servers/%s/server.config/java/java_fake2' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        self.system('rm %s' % fn)
        self.assertFalse(os.path.isfile(fn))
            
    '''def test_config_file_sectionless_delitem(self):
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

        self.assertEqual(conf['first':], 'hello')
        self.assertEqual(conf['first'::], 'hello')

        with self.assertRaises(TypeError): conf[::]
        with self.assertRaises(KeyError): conf['doesnotexist']
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

        with self.assertRaises(KeyError): conf['java':'madeup']
        with self.assertRaises(KeyError): conf['java':'madeup':]

        with self.assertRaises(SyntaxError): conf[5] = 12
        with self.assertRaises(SyntaxError): conf[None] = 12
        with self.assertRaises(SyntaxError): conf[{}] = 12
        with self.assertRaises(SyntaxError): conf[()] = 12

        conf.commit()
        self.assertTrue(os.path.isfile(self.CONFIG_FILES['sections']))

        with config_file(self.CONFIG_FILES['sections']) as conf:
            pass

    def test_reload_config(self):
        with config_file(self.CONFIG_FILES['sectionless']) as conf:
            conf.use_sections(False)
            conf['server-ip'] = '0.0.0.0'

        conf = config_file(self.CONFIG_FILES['sectionless'])
        self.assertFalse(conf._use_sections)
        self.assertEqual(conf['server-ip'], '0.0.0.0')
        self.assertEqual(conf['server-ip'::'0.0.0.0'], '0.0.0.0')

        with config_file(self.CONFIG_FILES['sectionless']) as conf:
            self.assertFalse(conf._use_sections)
            conf['server-ip'] = '127.0.0.1'

        conf = config_file(self.CONFIG_FILES['sectionless'])
        self.assertFalse(conf._use_sections)
        self.assertEqual(conf['server-ip'], '127.0.0.1')
        self.assertEqual(conf['server-ip'::'0.0.0.0'], '127.0.0.1')
    '''

if __name__ == "__main__":
    unittest.main()  
