""" utility functions """
import fcntl
from functools import wraps
import logging
import os
import socket
import struct
import sys

# pylint: disable=invalid-name,no-self-use,dangerous-default-value

SEEDNODE = 'cassandra-seed'
NODE = 'cassandra'
UNASSIGNED = 'UNASSIGNED'

# ---------------------------------------------------------
# logging setup

logging.basicConfig(format='%(levelname)s manage %(message)s',
                    stream=sys.stdout,
                    level=logging.getLevelName(
                        os.environ.get('LOG_LEVEL', 'INFO')))
log = logging.getLogger()

# reduce noise from requests logger
logging.getLogger('requests').setLevel(logging.WARN)

# ---------------------------------------------------------
# errors and debugging setup


def debug(fn=None, log_output=False):
    """
    Function/method decorator to trace calls via debug logging. Acts as
    pass-thru if not at LOG_LEVEL=DEBUG. Normally this would kill perf but
    this application doesn't have significant throughput.
    """
    def _decorate(fn, *args, **kwargs):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # because we have concurrent processes running we want
                # to tag each stack with an identifier for that process
                msg = "[{}]".format(sys.argv[1])
            except IndexError:
                msg = "[pre_start]"
            if len(args) > 0:
                cls_name = args[0].__class__.__name__.lower()
                name = '{}.{}'.format(cls_name, fn.__name__)
            else:
                name = fn.__name__
            log.debug('%s %s start', msg, name)
            out = apply(fn, args, kwargs)
            if log_output:  # useful for checking status flags
                log.debug('%s %s end: %s', msg, name, out)
            else:
                log.debug('%s %s end', msg, name)
            return out
        return wrapper
    if fn:
        return _decorate(fn)
    return _decorate


# ---------------------------------------------------------
# misc utility functions for setting up environment

def env(key, default, environ=os.environ, fn=None):
    """
    Gets an environment variable, trims away comments and whitespace,
    and expands other environment variables.
    """
    val = environ.get(key, default)
    try:
        val = val.split('#')[0]
        val = val.strip()
        val = os.path.expandvars(val)
    except (AttributeError, IndexError):
        # just swallow AttributeErrors for non-strings
        pass
    if fn:  # transformation function
        val = fn(val)
    return val


def to_flag(val):
    """
    Parse environment variable strings like "yes/no", "on/off",
    "true/false", "1/0" into a bool.
    """
    try:
        return bool(int(val))
    except ValueError:
        val = val.lower()
        if val in ('false', 'off', 'no', 'n'):
            return False
            # non-"1" or "0" string, we'll treat as truthy
        return bool(val)

def ping(host):
    """
    Returns True if host responds to a ping request
    """
    import subprocess, platform

    # Ping parameters as function of OS
    ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1"
    args = "ping " + " " + ping_str + " " + host
    need_sh = False if  platform.system().lower()=="windows" else True

    # Ping
    return subprocess.call(args, shell=need_sh) == 0

def get_ip(iface='eth0'):
    """
    Use Linux SIOCGIFADDR ioctl to get the IP for the interface.
    ref http://code.activestate.com/recipes/439094-get-the-ip-address\
        -associated-with-a-network-inter/
    """
    if sys.platform == 'darwin':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP  
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return socket.inet_ntoa(fcntl.ioctl(
            sock.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', iface[:15])
        )[20:24])
    