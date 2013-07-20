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
