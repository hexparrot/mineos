"""
    Verifies login/pw to shadow password databases
    and checks group memberships

"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"

def login(user, password):
    '''
    Modified version of:
    http://www.verious.com/qa/python-enter-password-and-compare-to-shadowed-password-database/
    '''
    
    from spwd import getspnam
    from crypt import crypt
    
    try:
        enc_pwd = getspnam(user)[1]
    except KeyError:
        raise KeyError("user '%s' not found" % user)
    else:
        if enc_pwd in ["NP", "!", "", None]:
            raise OSError("user '%s' has no password set" % user)
        elif enc_pwd in ["LK", "*"]:
            raise OSError('account is locked')
        elif enc_pwd == "!!":
            raise OSError('password is expired')

        if crypt(password, enc_pwd) == enc_pwd:
            return True
        else:
            raise ValueError("incorrect password")
    
def has_permissions(user, directory):
    from os import stat, geteuid
    from pwd import getpwuid
    from grp import getgrgid

    uid = stat(directory).st_uid
    gid = stat(directory).st_gid

    if user == getpwuid(uid).pw_name:
        return True
    elif user in getgrgid(gid).gr_mem:
        return True
    elif geteuid() == 0:
        return True
    return False

    
