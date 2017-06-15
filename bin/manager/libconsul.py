""" Module for Consul client wrapper and related tooling. """
from datetime import datetime, timedelta
import fcntl
import json
import os
import time

from manager.utils import debug, env, log, to_flag

# pylint: disable=import-error,invalid-name,dangerous-default-value
import consul as pyconsul

SESSION_CACHE_FILE = env('SESSION_CACHE_FILE', '/tmp/consul-session')
SESSION_NAME = env('SESSION_NAME', 'consul-session')
SESSION_TTL = env('SESSION_TTL', 25, fn=int)
MAX_SESSION = 3600


class Consul(object):
    """ Consul represents the Consul instance this node talks to """

    def __init__(self, envs=os.environ):
        """
        Figures out the Consul client hostname based on whether or
        not we're using a local Consul agent.
        """
        if env('CONSUL_AGENT', False, envs, fn=to_flag):
            self.host = 'localhost'
        else:
            self.host = env('CONSUL', 'consul', envs)
        self.client = pyconsul.Consul(host=self.host)

    def get(self, key):
        """
        Return the Value field for a given Consul key.
        Handles None results safely but lets all other exceptions
        just bubble up.
        """
        result = self.client.kv.get(key)
        if result[1]:
            return result[1]['Value']
        return None

    def put(self, key, value):
        """ Puts a value for the key; allows all exceptions to bubble up """
        return self.client.kv.put(key, value)

    def delete(self, key):
        return self.client.kv.delete(key)

    @debug(log_output=True)
    def get_session(self, key=SESSION_NAME, ttl=SESSION_TTL,
                    on_disk=SESSION_CACHE_FILE, cached=True):
        """
        Gets a Consul session ID from the on-disk cache or calls into
        `create_session` to generate a new one.
        We can't rely on storing Consul session IDs in memory because
        handler calls happen in subsequent processes. Here we create a
        session on Consul and cache the session ID to disk.
        Returns the session ID.
        """
        if not cached:
            return self.create_session(key, ttl)
        try:
            with open(on_disk, 'r+') as f:
                session_id = f.read()
        except IOError:
            session_id = self.create_session(key, ttl)
        if cached:
            with open(on_disk, 'w') as f:
                f.write(session_id)

        return session_id

    @debug(log_output=True)
    def create_session(self, key, ttl=120):
        """ Create a session on Consul and return the session ID """
        return self.client.session.create(name=key,
                                          behavior='release',
                                          ttl=ttl)

    @debug(log_output=True)
    def renew_session(self, session_id=None):
        """ Renews the session TTL on Consul """
        if not session_id:
            session_id = self.get_session()
        self.client.session.renew(session_id)

    @debug(log_output=True)
    def lock(self, key, value, session_id):
        """ Puts a key to Consul with an advisory lock """
        return self.client.kv.put(key, value, acquire=session_id)

    @debug
    def unlock(self, key, session_id):
        """ Clears a key in Consul and its advisory lock """
        return self.client.kv.put(key, "", release=session_id)

    @debug(log_output=True)
    def is_locked(self, key):
        """
        Checks a lock in Consul and returns the session_id if the
        lock is still valid, otherwise False
        """
        lock = self.client.kv.get(key)
        try:
            session_lock = lock[1]['Session']
            return session_lock
        except KeyError:
            return False

    @debug(log_output=True)
    def read_lock(self, key):
        """
        Checks a lock in Consul and returns the (session_id, value) if the
        lock is still valid, otherwise (None, None)
        """
        lock = self.client.kv.get(key)
        try:
            if not lock[1]:
                raise KeyError
            session_lock = lock[1]['Session']
            value = lock[1]['Value']
            return session_lock, value
        except KeyError:
            return None, None
