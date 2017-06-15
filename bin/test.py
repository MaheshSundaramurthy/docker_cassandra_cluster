from datetime import datetime, timedelta
import fcntl
import json
import logging
import os
import tempfile
import unittest

# pylint: disable=import-error
import consul as pyconsul
import mock

import manage
from manager.containerpilot import ContainerPilot
from manager.libconsul import Consul
from manager.utils import *


class TestConsul(unittest.TestCase):

    def setUp(self):
        self.environ = get_environ()

    def test_parse_with_consul_agent(self):
        self.environ['CONSUL_AGENT'] = '1'
        consul = Consul(self.environ)
        self.assertEqual(consul.host, 'localhost')

    def test_parse_without_consul_agent(self):
        self.environ['CONSUL_AGENT'] = '0'
        consul = Consul(self.environ)
        self.assertEqual(consul.host, 'my.consul.example.com')

        self.environ['CONSUL_AGENT'] = ''
        consul = Consul(self.environ)
        self.assertEqual(consul.host, 'my.consul.example.com')



class TestContainerPilotConfig(unittest.TestCase):

    def setUp(self):
        logging.getLogger().setLevel(logging.WARN)
        self.environ = get_environ()

    def tearDown(self):
        logging.getLogger().setLevel(logging.DEBUG)

    def test_parse_with_consul_agent(self):
        self.environ['CONSUL_AGENT'] = '1'
        cp = ContainerPilot()
        cp.load(envs=self.environ)
        self.assertEqual(cp.config['consul'], 'localhost:8500')
        cmd = cp.config['coprocesses'][0]['command']
        host_cfg_idx = cmd.index('-retry-join') + 1
        self.assertEqual(cmd[host_cfg_idx], 'my.consul.example.com')
        self.assertEqual(cp.state, UNASSIGNED)

    def test_parse_without_consul_agent(self):
        self.environ['CONSUL_AGENT'] = '0'
        cp = ContainerPilot()
        cp.load(envs=self.environ)
        self.assertEqual(cp.config['consul'], 'my.consul.example.com:8500')
        self.assertEqual(cp.config['coprocesses'], [])
        self.assertEqual(cp.state, UNASSIGNED)

        self.environ['CONSUL_AGENT'] = ''
        cp = ContainerPilot()
        cp.load(envs=self.environ)
        self.assertEqual(cp.config['consul'], 'my.consul.example.com:8500')
        self.assertEqual(cp.config['coprocesses'], [])
        self.assertEqual(cp.state, UNASSIGNED)

    def test_update(self):
        self.environ['CONSUL_AGENT'] = '1'
        cp = ContainerPilot()
        cp.state = REPLICA
        cp.load(envs=self.environ)
        temp_file = tempfile.NamedTemporaryFile()
        cp.path = temp_file.name

        # no update expected
        cp.update()
        with open(temp_file.name, 'r') as updated:
            self.assertEqual(updated.read(), '')

        # force an update
        cp.state = PRIMARY
        cp.update()
        with open(temp_file.name, 'r') as updated:
            config = json.loads(updated.read())
            self.assertEqual(config['consul'], 'localhost:8500')
            cmd = config['coprocesses'][0]['command']
            host_cfg_idx = cmd.index('-retry-join') + 1
            self.assertEqual(cmd[host_cfg_idx], 'my.consul.example.com')


class TestUtilsEnvironment(unittest.TestCase):

    def test_to_flag(self):
        self.assertEqual(to_flag('yes'), True)
        self.assertEqual(to_flag('Y'), True)
        self.assertEqual(to_flag('no'), False)
        self.assertEqual(to_flag('N'), False)
        self.assertEqual(to_flag('1'), True)
        self.assertEqual(to_flag('xxxxx'), True)
        self.assertEqual(to_flag('0'), False)
        self.assertEqual(to_flag('xxxxx'), True)
        self.assertEqual(to_flag(1), True)
        self.assertEqual(to_flag(0), False)

    def test_env_parse(self):

        os.environ['TestUtilsEnvironment'] = 'PASS'
        environ = {
            'A': '$TestUtilsEnvironment',
            'B': 'PASS  ',
            'C': 'PASS # SOME COMMENT'
        }
        self.assertEqual(env('A', '', environ), 'PASS')
        self.assertEqual(env('B', '', environ), 'PASS')
        self.assertEqual(env('C', '', environ), 'PASS')
        self.assertEqual(env('D', 'PASS', environ), 'PASS')


TEST_ENVIRON = {
    'CONSUL': 'my.consul.example.com',
    'CONSUL_AGENT': '1',

    'CONTAINERPILOT': 'file:///etc/containerpilot.json',
}

def get_environ():
    return TEST_ENVIRON.copy()


if __name__ == '__main__':
    unittest.main()
