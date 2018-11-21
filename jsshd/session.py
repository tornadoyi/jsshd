import asyncio
import asyncssh

from pyplus.collection import qdict
from jsshd.command import run_command


class SSHServerSession(asyncssh.SSHServerSession):
    def __init__(self, server):
        self.__user_server = server

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self): return False

    def exec_requested(self, command):
        async def run_callback(command):
            try:
                env = qdict(channel=self._chan)
                result = await run_command(command, env)
                if isinstance(result, BaseException):
                    self._chan.write(str(result) + '\n')
                    self._chan._report_response(False)
                else:
                    self._chan.write(result + '\n')
                    self._chan._report_response(True)
                self._chan.exit(0)
            except:
                pass

        # parse and check command
        asyncio.get_event_loop().create_task(run_callback(command))

        return None


