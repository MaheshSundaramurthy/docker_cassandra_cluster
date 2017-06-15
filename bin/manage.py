""" autopilotpattern/mysql ContainerPilot handlers """
from __future__ import print_function

import os
import random
import socket
import subprocess
import sys
import time
from datetime import datetime

# pylint: disable=invalid-name,no-self-use,dangerous-default-value
from manager.containerpilot import ContainerPilot
from manager.libconsul import Consul
from manager.libcassandra import CassandraService
from manager.utils import debug, get_ip, log, ping

random.seed()


class Node(object):
    def __init__(self, kvstore=None, cp=None, service=None):
        self.kvstore = kvstore
        self.cp = cp
        self.service = service
        self.hostname = socket.gethostname()
        self.name = 'cassandra-{}'.format(self.hostname)
        self.ip = get_ip()


def pre_start(node):
    # print(node)
    # time.sleep(random.random()*5)
    seeds = node.kvstore.get('cassandra_seeds')
    if seeds is None:
        node.service.set_seeds(None)
        node.kvstore.put('cassandra_seeds',node.ip)
    else:
        node.service.set_seeds(seeds)
        print("Now Im going to sleep")
        time.sleep(20*random.random())
        print("Now I finished sleeping")
    node.service.update_config(node.ip)
    return 0


def pre_stop(node):
    seeds = node.kvstore.get('cassandra_seeds')
    if node.ip in seeds:
        node.kvstore.delete('cassandra_seeds')
        return 0
    if not ping(seeds):
        node.kvstore.delete('cassandra_seeds')
    return 0


def basic_health(node):
    if node.service.getNodeStatus(node.ip) is None:
        ## if not healthy
        sys.exit(1)
    ## if healthy
    return 0

def health(node):
    if node.service.getNodeStatus(node.ip) is None:
        ## if not healthy
        sys.exit(1)
    ## if healthy
    return 0


def main():
    """
    Parse argument as command and execute that command with
    parameters containing the state of MySQL, ContainerPilot, etc.
    Default behavior is to run `pre_start` DB initialization.
    """
    if len(sys.argv) == 1:
        consul = Consul(envs={'CONSUL': os.environ.get('CONSUL', 'consul')})
        cmd = pre_start
    else:
        consul = Consul()
        try:
            cmd = globals()[sys.argv[1]]
        except KeyError:
            log.error('Invalid command: %s', sys.argv[1])
            sys.exit(1)

    cp = ContainerPilot()
    cass = CassandraService()
    cp.load()
    print(consul)
    node = Node(kvstore=consul, cp=cp, service=cass)

    cmd(node)

if __name__ == '__main__':
    main()
