#!/usr/bin/env python

import fuse, errno, stat, os, sys, time
from mineos import mc
from conf_reader import config_file
from functools import partial

BASE_DIR = '/var/games/minecraft'

fuse.fuse_python_api = (0, 2)

class mos_stat(fuse.Stat):
    def __init__(self, uid, gid):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = uid
        self.st_gid = gid
        self.st_size = 0

        self.st_atime = self.st_mtime = self.st_ctime = time.time()

    def touch(self, path):
        stat_result = os.stat(path)
        
        self.st_uid = stat_result.st_uid
        self.st_gid = stat_result.st_gid
        self.st_atime = stat_result.st_atime
        self.st_mtime = stat_result.st_mtime
        self.st_ctime = stat_result.st_ctime
        self.st_size = stat_result.st_size

    def directory(self):
        self.st_mode = stat.S_IFDIR | 0555
        self.st_nlink = 2
        self.st_size = 4096
        
        return self

    def console_device(self, server_name):
        self.st_mode = stat.S_IFREG | 0664
        self.st_nlink = 1

        try:
            instance = mc(server_name, None, BASE_DIR)
            self.st_size = os.path.getsize(instance.env['log'])
        except (KeyError, OSError, RuntimeError):
            self.st_size = 0

        return self

    def copy_stat(self, path):
        return os.stat(path)

    def file_as_directory(self, path):
        self.touch(path)
        
        self.st_mode = stat.S_IFDIR | 0555
        self.st_nlink = 2

        return self

    def config_as_file(self, path, section, option):
        self.touch(path)

        self.st_mode = stat.S_IFREG | 0664
        self.st_nlink = 1

        if section:
            size = len(config_file(path)[section:option])
            self.st_size = size + 1 if size else 0
        else:
            size = len(config_file(path)[option])
            self.st_size = size + 1 if size else 0

        return self

class minefs(fuse.Fuse):
    def __init__(self, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)
        self.mineos = partial(mc, owner=None, base_directory=BASE_DIR)

    @classmethod
    def components(self, path):
        return list(c for c in os.path.normpath(os.path.abspath(path)).split(os.sep) if c)

    @classmethod
    def named_components(self, path):
        from collections import namedtuple

        values = 'root_dir server_name file_name prop next_val'
        dirs = namedtuple('dir_components', values)
        d = [c for c in os.path.normpath(os.path.abspath(path)).split(os.sep) if c]
        d = d + [''] * (len(values.split(' ')) - len(d))
        return dirs(*d)

    def getattr(self, path):
        """Returns meta data for a given path"""

        def root():
            return st.copy_stat(BASE_DIR)

        def root_dir(components):
            if components.root_dir in ['servers','profiles']:
                return st.copy_stat(os.path.join(BASE_DIR, components.root_dir))
            return -errno.ENOENT

        def server_name(components):
            if components.server_name in mc.list_servers(BASE_DIR):
                return st.copy_stat(os.path.join(BASE_DIR, 'servers', components.server_name))
            return -errno.ENOENT

        def file_name(components):
            if components.file_name in ['banned-ips', 'banned-players', 'ops', 'white-list']:
                return st.file_as_directory(os.path.join(BASE_DIR,
                                                         components.root_dir,
                                                         components.server_name,
                                                         components.file_name) + '.txt')
            elif components.file_name in ['server.config', 'server.properties']:
                return st.file_as_directory(os.path.join(BASE_DIR,
                                                         components.root_dir,
                                                         components.server_name,
                                                         components.file_name))
            elif components.file_name == 'console':
                return st.console_device(components.server_name)
            return -errno.ENOENT

        def prop(components):
            if components.file_name == 'server.properties':
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name)
                try:
                    return st.config_as_file(p_,
                                             None,
                                             components.prop)
                except KeyError:
                    return -errno.ENOENT
            elif components.file_name == 'server.config':
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name)
                if components.prop in config_file(p_)[:]:
                    return st.file_as_directory(p_)
            elif components.file_name in ['banned-ips', 'banned-players']:
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name + '.txt')
                if prop in self.flat_config(p_, None, None, '|'):
                    return st.copy_stat(p_)
            elif components.file_name in ['ops', 'white-list']:
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name + '.txt')
                if prop in self.flat_config(p_, None, None):
                    return st.copy_stat(p_)
            return -errno.ENOENT

        def next_val(components):
            if components.file_name == 'server.config':
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name)
                try:
                    return st.config_as_file(p_, components.prop, components.next_val)
                except KeyError:
                    return -errno.ENOENT
            return -errno.ENOENT
        
        context = self.GetContext()
        st = mos_stat(context['uid'], context['gid'])

        components = self.named_components(path)

        if components.next_val:
            return next_val(components)
        elif components.prop:
            return prop(components)
        elif components.file_name:
            return file_name(components)
        elif components.server_name:
            return server_name(components)
        elif components.root_dir:
            return root_dir(components)
        else:
            return root()

    def flat_config(self, path, add, remove, partition_by=None):
        with open(path, 'r') as conf:
            lines = list(i.strip() for i in conf.readlines())
            if add:
                lines.append(add)

        if add or remove:
            with open(path, 'w') as conf:
                for line in lines:
                    if partition_by:
                        if line.partition(partition_by)[0] != remove:
                            conf.write('%s\n' % line)
                    else:
                        if line != remove:
                            conf.write('%s\n' % line)

        if partition_by:
            return [v.partition(partition_by)[0] for v in lines if v.strip() and not v.startswith('#')]
        else:
            return [v for v in lines if not v.startswith('#') and v.strip()]

    def readdir(self, path, offset):
        ''' lists pwd files given a path '''

        def root():
            yield fuse.Direntry('servers')
            yield fuse.Direntry('profiles')

        def root_dir(components):
            if components.root_dir == 'servers':
                for s in mc.list_servers(BASE_DIR):
                    yield fuse.Direntry(s)
            elif components.root_dir == 'profiles':
                for p in mc.list_profiles(BASE_DIR):
                    yield fuse.Direntry(p)

        def server_name(components):
            if components.server_name in mc.list_servers(BASE_DIR):
                yield fuse.Direntry('server.config')
                yield fuse.Direntry('server.properties')
                yield fuse.Direntry('banned-players')
                yield fuse.Direntry('banned-ips')
                yield fuse.Direntry('white-list')
                yield fuse.Direntry('ops')
                yield fuse.Direntry(name='console', type=stat.S_IFCHR)

        def file_name(components):
            if components.file_name == 'server.properties':
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name)
                for i in config_file(p_)[:]:
                    yield fuse.Direntry(name=i, type=stat.S_IFREG)
            elif components.file_name == 'server.config':
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name)
                for i in config_file(p_)[:]:
                    yield fuse.Direntry(name=i, type=stat.S_IFDIR)
            elif components.file_name == 'banned-players':
                for i in self.flat_config(os.path.join(BASE_DIR,
                                                       components.root_dir,
                                                       components.server_name,
                                                       components.file_name + '.txt'),
                                          None,
                                          None,
                                          partition_by='|'):
                    yield fuse.Direntry(name=i, type=stat.S_IFREG)
            elif components.file_name in ['banned-ips', 'white-list', 'ops']:
                for i in self.flat_config(os.path.join(BASE_DIR,
                                                       components.root_dir,
                                                       components.server_name,
                                                       components.file_name + '.txt'),
                                          None,
                                          None):
                    yield fuse.Direntry(name=i, type=stat.S_IFREG)

        def prop(components):
            if components.file_name == 'server.config':
                p_ = os.path.join(BASE_DIR,
                                  components.root_dir,
                                  components.server_name,
                                  components.file_name)
                for i in config_file(p_)[components.prop:]:
                    yield fuse.Direntry(name=i, type=stat.S_IFREG)

        components = self.named_components(path)

        for r in ['.', '..']:
            yield fuse.Direntry(r)

        if components.prop:
            for d in prop(components): yield d
        elif components.file_name:
            for d in file_name(components): yield d
        elif components.server_name:
            for d in server_name(components): yield d
        elif components.root_dir:
            for d in root_dir(components): yield d
        else:
            for d in root(): yield d
                        

    def read(self, path, size, offset):
        components = self.named_components(path)

        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, BASE_DIR)
            return bytes(instance.server_config[components.prop:components.next_val] + '\n')
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, BASE_DIR)
            return bytes(instance.server_properties[components.prop] + '\n')
        elif components.file_name == 'console':
            instance = mc(components.server_name, None, BASE_DIR)
            with open(instance.env['log'], 'r') as log:
                return bytes(''.join(log.readlines()))
            

    def create(self, path, mode=None, umask=None):
        components = self.named_components(path)

        if components.file_name == 'server.config':
            p_ = os.path.join(BASE_DIR,
                              components.root_dir,
                              components.server_name,
                              components.file_name)
            
            if components.next_val:
                with config_file(p_) as sc:
                    if components.prop not in sc[:]:
                        sc.add_section(components.prop)
                    sc[components.prop:components.next_val] = ''
                return 0
            return -errno.EPERM
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, BASE_DIR)
            instance.server_properties[components.prop] = ''
            instance.server_properties.commit()
            return 0
        elif components.file_name in ['banned-ips', 'banned-players', 'white-list', 'ops']:
            self.flat_config(os.path.join(BASE_DIR,
                                          components.root_dir,
                                          components.server_name,
                                          components.file_name + '.txt'),
                             components.prop,
                             None)

    def mkdir(self, path, mode):
        components = self.named_components(path)

        print '*** MKDIR'

        if components.file_name == 'server.config':
            if components.next_val:
                print 'trying to create a directory within a section'
                return -errno.EPERM
            instance = mc(components.server_name, None, BASE_DIR)
            with instance.server_config as sc:
                sc.add_section(components.prop)
                return 0
        elif components.file_name == 'server.properties':
            print 'trying to create a directory within sp'
            return -errno.EPERM

    def write(self, path, buf, offset):
        print "*** WRITE"
        components = self.named_components(path)

        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, BASE_DIR)
            instance.server_config[components.prop:components.next_val] = str(buf).partition('\n')[0]
            instance.server_config.commit()
            return len(buf)
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, BASE_DIR)
            instance.server_properties[components.prop] = str(buf).partition('\n')[0]
            instance.server_properties.commit()
            return len(buf)
        elif components.file_name == 'console':
            instance = mc(components.server_name, None, BASE_DIR)
            try:
                instance._command_stuff(buf)
            except RuntimeError:
                return -errno.EHOSTDOWN
            return len(buf)
        
        return -errno.EIO

    def truncate(self, path, length):
        print "*** TRUNCATE"

    def unlink(self, path):
        print "*** UNLINK"

        components = self.named_components(path)
        
        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, BASE_DIR)
            del instance.server_config[components.prop:components.next_val]
            instance.server_config.commit()
            return 0
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, BASE_DIR)
            del instance.server_properties[components.prop]
            instance.server_properties.commit()
            return 0
        elif components.file_name in ['banned-ips', 'white-list', 'ops']:
            self.flat_config(os.path.join(BASE_DIR,
                                          components.root_dir,
                                          components.server_name,
                                          components.file_name + '.txt'), '', components.prop)
            return 0
        elif components.file_name == 'banned-players':
            self.flat_config(os.path.join(BASE_DIR,
                                          components.root_dir,
                                          components.server_name,
                                          components.file_name + '.txt'), '', components.prop, '|')
            return 0

    def utimens(self, path, ts_acc, ts_mod):
        print "*** UTIMENS"

if __name__ == '__main__':
    server = minefs()
    server.parse(errex=1)
    server.main()
