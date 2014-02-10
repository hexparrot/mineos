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
        for d in [
            'fakedir',
            'servers/fakeserver',
            'servers/fakeserver/server.config',
            'servers/fakeserver/server.config/java',
            'servers/fakeserver/server.config/javac',
            'profiles/fakeprofile',
            'servers/%s/server.config/javac' % REAL_SERVER]:
            
            with self.assertRaises(subprocess.CalledProcessError) as e:
                self.call('ls {0}'.format(d))
                self.assertEqual(e.returncode, errno.ENOENT)

    def test_cd_fake_dir(self):
        for d in [
            'fakeo',
            'servers/fake',
            'servers/fake/server.config',
            'servers/fake/server.config/java',
            'servers/fake/server.properties/javac'
            'servers/%s/server.config/fake' % REAL_SERVER
            ]:
            
            with self.assertRaises(OSError) as e:
                self.call('cd {0}'.format(d))
                self.assertEqual(e.returncode, errno.ENOENT)

    def test_create_server_property(self):
        fn = 'servers/{0}/server.properties/newprop1'.format(REAL_SERVER)
        self.system('touch %s' % fn)
        self.assertTrue(os.path.isfile(fn))

    def test_truncate_server_property(self):
        fn = 'servers/{0}/server.properties/newprop2'.format(REAL_SERVER)
        self.system('touch %s' % fn)
        self.system('echo 5 > %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '5\n')

    def test_append_server_property(self):
        fn = 'servers/{0}/server.properties/newprop3'.format(REAL_SERVER)
        self.system('touch %s' % fn)
        self.system('echo 5 > %s' % fn)
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '5\n')

    def test_create_server_config(self):
        fn = 'servers/{0}/server.config/java/java_fake1'.format(REAL_SERVER)
        self.system('touch %s' % fn)
        self.assertTrue(os.path.isfile(fn))

    def test_truncate_server_config(self):
        fn = 'servers/{0}/server.config/java/java_fake2'.format(REAL_SERVER)
        self.system('touch {0}'.format(fn))
        self.system('echo 256 > {0}'.format(fn))
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '256\n')

    def test_append_server_config(self):
        fn = 'servers/{0}/server.config/java/java_fake3'.format(REAL_SERVER)
        self.system('touch {0}'.format(fn))
        self.system('echo 256 >> {0}'.format(fn))
        self.assertTrue(os.path.isfile(fn))
        with open(fn, 'r') as newprop:
            n = newprop.readlines()
            self.assertEqual(len(n), 1)
            self.assertEqual(n[0], '256\n')

    def test_create_server_config_section(self):
        fn = 'servers/{0}/server.config/newsect'.format(REAL_SERVER)
        self.call('mkdir -p {0}'.format(fn))
        self.assertTrue(os.path.isdir(fn))

    def test_delete_server_property(self):
        fn = 'servers/{0}/server.properties/newprop2'.format(REAL_SERVER)
        self.system('touch {0}'.format(fn))
        self.assertTrue(os.path.isfile(fn))
        self.system('rm {0}'.format(fn))
        self.assertFalse(os.path.isfile(fn))

    def test_delete_server_config(self):
        fn = 'servers/{0}/server.config/java/java_fake2'.format(REAL_SERVER)
        self.system('touch {0}'.format(fn))
        self.assertTrue(os.path.isfile(fn))
        self.system('rm {0}'.format(fn))
        self.assertFalse(os.path.isfile(fn))

    def test_write_console_server_down(self):
        fn = 'servers/{0}/console'.format(REAL_SERVER)
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.call('echo "test" > {0}'.format(fn))
            self.assertEqual(e.returncode, errno.EHOSTDOWN)

if __name__ == "__main__":
    unittest.main()  
