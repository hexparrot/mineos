#!/usr/bin/env python2.7

import unittest
import os
import time
import pycurl
import json

from mineos import mc
from shutil import rmtree
from urllib import urlencode
from StringIO import StringIO

VANILLA_PROFILE = {
    'name': 'vanilla',
    'type': 'standard_jar',
    'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.2/minecraft_server.1.6.2.jar',
    'save_as': 'minecraft_server.jar',
    'run_as': 'minecraft_server.jar',
    'action': 'download',
    'ignore': '',
    }

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

class TestMineOS(unittest.TestCase):
    def setUp(self):
        self.c = pycurl.Curl()
        self.c.setopt(pycurl.HTTPHEADER, ["Accept:"])
        
        self.b = StringIO()
        self.c.setopt(pycurl.WRITEFUNCTION, self.b.write)
        self.c.setopt(pycurl.FOLLOWLOCATION, 1)
        self.c.setopt(pycurl.MAXREDIRS, 5)
        self.c.setopt(pycurl.POST, 1)

    def tearDown(self):
        self.c.close()
        for d in mc.DEFAULT_PATHS.values():
            try:
                rmtree(os.path.join('/home/mc', d))
            except OSError:
                continue

    def test_root(self):
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080")
        self.c.setopt(pycurl.POSTFIELDS, urlencode({}))
        self.c.perform()

        with self.assertRaises(ValueError):
            e = json.loads(self.b.getvalue())

    def test_create_servers(self):
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080/server")

        d = {
            'cmd': 'create',
            'server_name': 'online'
            }

        self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
        self.c.perform()

        e = json.loads(self.b.getvalue())
        self.assertEqual(e['result'], 'success')

        instance = mc(d['server_name'])
        self.assertTrue(d['server_name'] in instance.list_servers())

        self.b = StringIO()

        d = {
            'cmd': 'list_servers'
            }

        self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
        self.c.setopt(pycurl.WRITEFUNCTION, self.b.write)
        self.c.perform()
        
        e = json.loads(self.b.getvalue())
        self.assertEqual(e['payload'], ['online'])

    def test_properties_offline(self):
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080/server")
        instance = mc('online')
        instance.create()

        pairs = [
            ('up', False),
            ('java_pid', None),
            ('screen_pid', None),
            ('server_name', 'online'),
            ('base', '/home/mc'),
            ('port', 25565),
            ('ip_address', '0.0.0.0'),
            ('memory', '0'),
            ]

        for k,v in pairs:
            d = {
                'cmd': k,
                'server_name': 'online'}
            b = StringIO()

            self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
            self.c.setopt(pycurl.WRITEFUNCTION, b.write)
            self.c.perform()

            e = json.loads(b.getvalue())
            self.assertEqual(e['payload'], v)

    #@unittest.skip("demonstrating skipping")
    def test_properties_online(self):
        global VANILLA_PROFILE
        
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080/server")
        instance = mc('online')
        instance.create()
        instance.define_profile(VANILLA_PROFILE)
        instance.update_profile('vanilla')
        instance.profile = 'vanilla'
        instance.start()
        time.sleep(20)

        pairs = [
            ('up', False),
            ('java_pid', None),
            ('screen_pid', None),
            ('memory', '0'),
            ]

        for k,v in pairs:
            d = {
                'cmd': k,
                'server_name': 'online'}
            b = StringIO()

            self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
            self.c.setopt(pycurl.WRITEFUNCTION, b.write)
            self.c.perform()

            e = json.loads(b.getvalue())
            self.assertNotEqual(e['payload'], v)

        instance._command_stuff('stop')
        time.sleep(5)
        try:
            instance.kill()
        except:
            pass
        finally:
            time.sleep(2)

    def test_runtime_warning(self):
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080/server")
        instance = mc('online')

        d = {
            'cmd': 'start',
            'server_name': 'online'
            }

        self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
        self.c.setopt(pycurl.WRITEFUNCTION, self.b.write)
        self.c.perform()

        e = json.loads(self.b.getvalue())
        self.assertEqual(e['result'], 'warning')

    def test_runtime_error(self):
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080/server")
        instance = mc('online')
        instance.create()

        d = {
            'cmd': 'kill',
            'server_name': 'online'
            }

        self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
        self.c.setopt(pycurl.WRITEFUNCTION, self.b.write)
        self.c.perform()

        e = json.loads(self.b.getvalue())
        self.assertEqual(e['result'], 'error')

    def test_properties_setting(self):
        global VANILLA_PROFILE
        
        self.c.setopt(pycurl.URL, "http://127.0.0.1:8080/server")
        instance = mc('online')

        d = {
            'cmd': 'profile',
            'server_name': 'online',
            'name': 'vanilla'
            }
        
        instance.create()
        instance.define_profile(VANILLA_PROFILE)
        instance.update_profile(d['name'])

        self.assertIsNone(instance.profile)

        self.c.setopt(pycurl.POSTFIELDS, urlencode(d))
        self.c.setopt(pycurl.WRITEFUNCTION, self.b.write)
        self.c.perform()

        e = json.loads(self.b.getvalue())

        self.assertEqual(e['result'], 'success')
        self.assertEqual(e['payload'], d['name'])

        #because config was changed by a subprocess
        instance._load_config()
        self.assertEquals(instance.profile, d['name'])

if __name__ == "__main__":
    unittest.main()

    '''

    fast = unittest.TestSuite()
    fast.addTest(TestMineOS('test_prune'))
    unittest.TextTestRunner().run(fast)
    '''
    
