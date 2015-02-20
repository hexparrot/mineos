"""
    A python script to get procfs info (/proc)
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

import os
from binascii import b2a_qp

_PROCFS_PATHS = ['/proc',
                 '/usr/compat/linux/proc']

for procfs in _PROCFS_PATHS:
    try:
        with open(os.path.join(procfs, 'uptime'), 'rb') as procdump:
            _procfs = procfs
            break
    except IOError:
        continue
    else:
        raise RuntimeError('No suitable procfs filesystem found')

def pids():  
    return set(int(pid) for pid in os.listdir(_procfs) if pid.isdigit())

def pid_cmdline():
    """
    Generator: all processes' pids

    """    
    for pid in pids():
        try:
            with open(os.path.join(_procfs, str(pid), 'cmdline'), 'rb') as fh:
                cmdline = b2a_qp(fh.read())
                cmdline = cmdline.replace('=00', ' ').replace('=\n', '').strip()
                yield (pid, cmdline)
        except IOError:
            continue

def entries(pid, page):
    with open(os.path.join(_procfs, str(pid), page)) as proc_status:
        for line in proc_status:
            split = b2a_qp(line).partition(':')
            yield (split[0].strip(), split[2].strip())

def path_owner(path):
    from pwd import getpwuid
    st = os.stat(path)
    uid = st.st_uid
    return getpwuid(uid).pw_name

def pid_owner(pid):
    from pwd import getpwuid
    
    try:
        status_page = dict(entries(pid, 'status'))
    except IOError:
        raise IOError('Process %s does not exist' % pid)
    else:
        return getpwuid(int(status_page['Uid'].partition('\t')[0]))

def pid_group(pid):
    from grp import getgrgid

    try:
        status_page = dict(entries(pid, 'status'))
    except IOError:
        raise IOError('Process %s does not exist' % pid)
    else:
        return getgrgid(int(status_page['Gid'].partition('\t')[0]))

def proc_uptime():
    raw = entries('', 'uptime').next()[0]
    return tuple(float(v) for v in raw.split())

def proc_loadavg():
    raw = entries('', 'loadavg').next()[0]
    return tuple(float(v) for v in raw.split()[:3])

def human_readable(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n

def disk_free(path):
    """
    df stats of filesystem.
    Keyword Arguments:
    path -- path to filesystem to poll
    
    Returns:
    namedtuple (total, used, free)
    
    Thank you, Giampaolo Rodola
    http://code.activestate.com/recipes/577972-disk-usage/
    
    """
    import collections
    
    _ntuple_diskusage = collections.namedtuple('usage', 'total used free')
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return _ntuple_diskusage(human_readable(total),
                             human_readable(used),
                             human_readable(free))

def disk_usage(path):
    return sum(os.path.getsize(os.path.join(dirpath,filename))
               for dirpath, dirnames, filenames in os.walk(path)
               for filename in filenames)

def tail(f, window=50):
    """
    Returns the last `window` lines of file `f` as a list.
    http://stackoverflow.com/a/7047765/1191579
    """
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window + 1
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if bytes - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            data.insert(0, f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.insert(0, f.read(bytes))
        linesFound = data[0].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines()[-window:]

def git_hash(path):
    """Returns the tag or short commit hash of a git path"""
    from distutils.spawn import find_executable
    from subprocess import check_output
    from shlex import split

    try:
        return check_output(split('%s describe --always' % find_executable('git')), cwd=path).strip()
    except:
        return ''
