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

os.chdir(MOUNT_POINT)

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
                                  stdout=nulldev,
                                  cwd=MOUNT_POINT)

    def test_external_setup(self):
        self.assertTrue(os.path.exists(MOUNT_POINT))

    def test_root_dir(self):
        for d in ['profiles', 'servers']:
            self.assertTrue(os.path.isdir(os.path.join(MOUNT_POINT,d)))

    def test_server_dir(self):
        for s in next(os.walk('servers'))[1]:
            for d in ['server.properties', 'server.config',
                      'banned-ips', 'banned-players',
                      'white-list']:
                self.assertTrue(os.path.isdir(os.path.join('servers', s, d)))

    def test_regular_files(self):
        for s in next(os.walk('servers'))[1]:
            for d in ['server.properties',
                      'banned-ips', 'banned-players',
                      'white-list']:
                prefix_path = os.path.join('servers',s,d)
                for f in os.listdir(prefix_path):
                    self.assertTrue(os.path.isfile(os.path.join(prefix_path, f)))

            prefix_path = os.path.join('servers', s, 'server.config')
            for d in os.listdir(prefix_path):
                full_path = os.path.join(prefix_path, d)
                self.assertTrue(os.path.isdir(full_path))
                for f in os.listdir(full_path):
                    self.assertTrue(os.path.isfile(os.path.join(full_path, f)))
                         
    def test_ls_fake_dir(self):
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls fakedir')
            self.assertEqual(e.returncode, errno.ENOENT)
                 
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % os.path.join('servers/fakeserver'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % os.path.join('servers/fakeserver/server.config'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % os.path.join('servers/fakeserver/server.config/java'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % os.path.join('servers/fakeserver/server.config/javac'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % os.path.join('profiles/fakeprofile'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('ls %s' % os.path.join('servers/%s/server.config/javac' % REAL_SERVER))
            self.assertEqual(e.returncode, errno.ENOENT)

    def test_cd_fake_dir(self):
        with self.assertRaises(OSError) as e:
            self.call('cd %s' % os.path.join('fakeo'))
            self.assertEqual(e.returncode, errno.ENOENT)
            
        with self.assertRaises(OSError) as e:
            self.call('cd %s' % os.path.join('servers/fake'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % os.path.join('servers/fake/server.config'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % os.path.join('servers/fake/server.config/java'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % os.path.join('servers/fake/server.properties/javac'))
            self.assertEqual(e.returncode, errno.ENOENT)

        with self.assertRaises(OSError) as e:
            self.call('cd %s' % os.path.join('servers/%s/server.config/fake' % REAL_SERVER))
            self.assertEqual(e.returncode, errno.ENOENT)

    def test_create_server_property(self):
        fn = os.path.join('servers/%s/server.properties/newprop' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.system('echo 5 >> %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '5\n')

    def test_create_server_config(self):
        fn = os.path.join('servers/%s/server.config/java/java_fake' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.system('echo 256 >> %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '256\n')

    def test_create_server_config_section(self):
        fn = os.path.join('servers/%s/server.config/newsect' % REAL_SERVER)
        self.call('mkdir -p %s' % fn)
        
        self.assertTrue(os.path.isdir(fn))

    def test_delete_server_property(self):
        fn = os.path.join('servers/%s/server.properties/newprop2' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        self.system('rm %s' % fn)
        self.assertFalse(os.path.isfile(fn))

    def test_delete_server_config(self):
        fn = os.path.join('servers/%s/server.config/java/java_fake2' % REAL_SERVER)
        self.system('touch %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        self.system('rm %s' % fn)
        self.assertFalse(os.path.isfile(fn))

if __name__ == "__main__":
    unittest.main()  
