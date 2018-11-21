
import signal
import sys
import asyncio
import asyncssh
import logging

from jsshd.user import UserEntity


class Service(object):
    def __init__(self, config):
        self.__config = config
        self.__server = None

    def __call__(self, *args, **kwargs):
        # set asyncssh log
        asyncssh.set_log_level(logging.DEBUG)
        sh = logging.StreamHandler()
        asyncssh.logger.logger.addHandler(sh)


        # catch exit signal
        def sigint_handler(signum, frame):
            print('catched interrupt signal and ready to exit')
            asyncio.get_event_loop().stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGHUP, sigint_handler)
        signal.signal(signal.SIGTERM, sigint_handler)

        # run loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.__async_loop())
        loop.close()


    @property
    def config(self): return self.__config


    async def __async_loop(self):
        # create server
        self.__server = await asyncssh.create_server(
            lambda : UserEntity(self),
            '',
            self.__config.port,
            server_host_keys=self.__config.server_host_keys,
            allow_scp=True,
        )


        await asyncio.sleep(3600.0)



    def on_user_auth_completed(self, server):
        pass


    def on_user_connection_lost(self, server):
        pass






