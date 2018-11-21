import os
from functools import partial

import asyncssh

from jsshd.session import SSHServerSession
from jsshd.bridge import Bridge



class UserEntity(asyncssh.SSHServer):
    def __init__(self, service):
        self.__service = service
        self.__bridge = None
        self.__session = None


    @property
    def connection(self): return self.__conn

    @property
    def bridge(self): return self.__bridge

    @property
    def session(self): return self.__session


    def connection_made(self, conn):
        self.__conn = conn

    def connection_lost(self, exc):
        self.__service.on_user_connection_lost(self)


    def password_auth_supported(self): return False

    def public_key_auth_supported(self): return True

    def validate_public_key(self, username, key):
        # check target ip

        # check public key

        return True


    def auth_completed(self):
        self.__service.on_user_auth_completed(self)


    def connection_requested(self, dest_host, dest_port, orig_host, orig_port):
        assert self.__bridge is None

        config = self.__service.config
        self.__bridge = Bridge(orig_host, orig_port,
                               {
                                   'server_host_keys': config.server_host_keys
                               },
                               {
                                   'host': dest_host,
                                   'port': dest_port,
                                   'client_keys' : config.client_keys,
                                   'known_hosts': None
                               })
        return self.__bridge.initialize()




    def session_requested(self):
        assert self.__session is None
        self.__session = SSHServerSession(self)
        return self.__session


