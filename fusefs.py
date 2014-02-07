#!/usr/bin/env python

import fuse, errno, stat, os, sys, time
from mineos import mc

MINEOS_SKELETON = '/var/games/minecraft'

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

        from conf_reader import config_file
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
        ''' returns meta data for a path '''
        context = self.GetContext()
        st = mos_stat(context['uid'], context['gid'])

        components = self.components(path)

        try:
            root_dir = components.pop(0)
        except IndexError:
            return st.directory()

        #/root_dir/server_name/file_name/prop/next_val
        if root_dir == 'servers':
            try:
                server_name = components.pop(0)
            except IndexError:
                return st.copy_stat(os.path.join(MINEOS_SKELETON, root_dir))
            else:
                try:
                    file_name = components.pop(0)
                except IndexError:
                    if server_name in mc.list_servers(MINEOS_SKELETON):
                        return st.copy_stat(os.path.join(MINEOS_SKELETON, root_dir, server_name))
                else:
                    try:
                        prop = components.pop(0)
                    except IndexError:
                        if server_name in mc.list_servers(MINEOS_SKELETON):
                            if file_name in ['banned-ips', 'banned-players', 'ops', 'white-list']:
                                return st.file_as_directory(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name) + '.txt')
                            elif file_name in ['server.config', 'server.properties']:
                                return st.file_as_directory(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name))
                    else:
                        if file_name == 'server.properties':
                            try:
                                return st.config_as_file(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name), None, prop)
                            except KeyError:
                                return -errno.ENOENT
                        elif file_name == 'server.config':
                            try:
                                next_val = components.pop(0)
                                return st.config_as_file(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name), prop, next_val)
                            except IndexError:
                                return st.file_as_directory(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name))
                            except KeyError:
                                    return -errno.ENOENT
                        elif file_name == 'banned-players':
                            p_ = os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name + '.txt')
                            if prop in self.flat_config(p_, None, None, '|'):
                                return st.copy_stat(p_)
                        elif file_name in ['banned-ips', 'ops', 'white-list']:
                            p_ = os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name + '.txt')
                            if prop in self.flat_config(p_, None, None):
                                return st.copy_stat(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name + '.txt'))

        elif root_dir == 'profiles':
            try:
                profile_name = components.pop(0)
            except IndexError:
                return st.directory()
            else:
                if profile_name in mc.list_profiles(MINEOS_SKELETON):
                    return st.copy_stat(os.path.join(MINEOS_SKELETON, root_dir, profile_name))
                

        return -errno.ENOENT

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
        for r in ['.', '..']:
            yield fuse.Direntry(r)

        components = self.components(path)

        try:
            root_dir = components.pop(0)
        except IndexError:
            yield fuse.Direntry('servers')
            yield fuse.Direntry('profiles')
            raise StopIteration

        #/root_dir/server_name/file_name/prop/next_val
        if root_dir == 'servers':
            try:
                server_name = components.pop(0)
            except IndexError:
                for s in mc.list_servers(MINEOS_SKELETON):
                    yield fuse.Direntry(s)
                raise StopIteration
            else:
                try:
                    file_name = components.pop(0)
                except IndexError:
                    if server_name in mc.list_servers(MINEOS_SKELETON):
                        yield fuse.Direntry('server.config')
                        yield fuse.Direntry('server.properties')
                        yield fuse.Direntry('banned-players')
                        yield fuse.Direntry('banned-ips')
                        yield fuse.Direntry('white-list')
                        yield fuse.Direntry('ops')
                else:
                    try:
                        next_val = components.pop(0)
                    except IndexError:
                        if file_name == 'server.properties':
                            instance = mc(server_name, None, MINEOS_SKELETON)
                            for i in getattr(instance, 'server_properties')[:]:
                                yield fuse.Direntry(name=i, type=stat.S_IFREG)
                        elif file_name == 'server.config':
                            instance = mc(server_name, None, MINEOS_SKELETON)
                            for i in getattr(instance, 'server_config')[:]:
                                yield fuse.Direntry(name=i, type=stat.S_IFREG)
                        elif file_name == 'banned-players':
                            for i in self.flat_config(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name) + '.txt',
                                                      None,
                                                      None,
                                                      partition_by='|'):
                                yield fuse.Direntry(name=i, type=stat.S_IFREG)
                        elif file_name in ['banned-ips', 'white-list', 'ops']:
                            for i in self.flat_config(os.path.join(MINEOS_SKELETON, root_dir, server_name, file_name) + '.txt',
                                                      None,
                                                      None):
                                yield fuse.Direntry(name=i, type=stat.S_IFREG)
                    else:
                        if file_name == 'server.config':
                            instance = mc(server_name, None, MINEOS_SKELETON)
                            for i in getattr(instance, 'server_config')[next_val:]:
                                yield fuse.Direntry(name=i, type=stat.S_IFREG)
        elif root_dir == 'profiles':
            try:
                profile_name = components.pop(0)
            except IndexError:
                for p in mc.list_profiles(MINEOS_SKELETON):
                    yield fuse.Direntry(p)
                raise StopIteration
            else:
                if profile_name in mc.list_profiles(MINEOS_SKELETON):
                    pass

    def read(self, path, size, offset):
        components = self.named_components(path)

        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            return bytes(instance.server_config[components.prop:components.next_val] + '\n')
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            return bytes(instance.server_properties[components.prop] + '\n')

    def create(self, path, mode=None, umask=None):
        components = self.named_components(path)

        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            instance.server_config[components.prop:components.next_val] = ''
            instance.server_config.commit()
            return 0
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            instance.server_properties[components.prop] = ''
            instance.server_properties.commit()
            return 0
        elif components.file_name in ['banned-ips', 'banned-players', 'white-list', 'ops']:
            self.flat_config(os.path.join(MINEOS_SKELETON,
                                          components.root_dir,
                                          components.server_name,
                                          components.file_name + '.txt'),
                             components.prop,
                             None)

    def write(self, path, buf, offset):
        print "*** WRITE"
        #echo "this" >> file
        components = self.named_components(path)

        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            instance.server_config[components.prop:components.next_val] = str(buf).partition('\n')[0]
            instance.server_config.commit()
            return len(buf)
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            instance.server_properties[components.prop] = str(buf).partition('\n')[0]
            instance.server_properties.commit()
            return len(buf)
        
        return -errno.EIO

    def truncate(self, path, length):
        print "*** TRUNCATE"
        self.create(path)

    def unlink(self, path):
        print "*** UNLINK"

        components = self.named_components(path)
        
        if components.file_name == 'server.config':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            del instance.server_config[components.prop:components.next_val]
            instance.server_config.commit()
            return 0
        elif components.file_name == 'server.properties':
            instance = mc(components.server_name, None, MINEOS_SKELETON)
            del instance.server_properties[components.prop]
            instance.server_properties.commit()
            return 0
        elif components.file_name in ['banned-ips', 'white-list', 'ops']:
            self.flat_config(os.path.join(MINEOS_SKELETON,
                                          components.root_dir,
                                          components.server_name,
                                          components.file_name + '.txt'), '', components.prop)
            return 0
        elif components.file_name == 'banned-players':
            self.flat_config(os.path.join(MINEOS_SKELETON,
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
