import asyncio
from asyncssh.misc import ChannelOpenError
from asyncssh.constants import OPEN_CONNECT_FAILED

class Protocol(object):
    def __init__(self):
        self.__transport = None
        self.__eof_received = False
        self.__listeners = []

    def connection_made(self, transport, *args, **kwargs):
        self.__transport = transport
        self.__notify('connection_made', transport, source=self)

    def connection_lost(self, exc, *args, **kwargs): self.__notify('connection_lost', exc, source=self)

    def write(self, data, *args, **kwargs):
        self.__transport.write(data)

    def write_eof(self, *args, **kwargs):
        try:
            self.__transport.write_eof()
        except OSError: # pragma: no cover
            pass


    def was_eof_received(self, *args, **kwargs): return self.__eof_received

    def session_started(self, *args, **kwargs): self.__notify('session_started', source=self)

    def data_received(self, data, datatype=None, *args, **kwargs): self.__notify('data_received', data, datatype=None, source=self)

    def eof_received(self, *args, **kwargs):
        self.__eof_received = True
        self.__notify('eof_received', source=self)
        return self.__eof_received

    def pause_reading(self, *args, **kwargs):
        self._transport.pause_reading()

    def resume_reading(self, *args, **kwargs):
        self._transport.resume_reading()

    def pause_writing(self, *args, **kwargs): self.__notify('pause_writing', source=self)

    def resume_writing(self, *args, **kwargs): self.__notify('resume_writing', source=self)

    def close(self, *args, **kwargs):
        self._transport.close()
        self._transport = None


    def add_listener(self, listener):
        if listener in self.__listeners: return
        self.__listeners.append(listener)

    def del_listener(self, listener):
        try:
            index = self.__listeners.index(listener)
            del self.__listeners[index]
        except:
            pass


    def __notify(self, func, *args, **kwargs):
        for l in self.__listeners:
            h = getattr(l, func, None)
            if h is None: continue
            h(*args, **kwargs)



class Bridge(object):
    def __init__(self, src_factory=None, dst_factory=None):
        super(Bridge, self).__init__()
        self.__src_factory = src_factory if src_factory is not None else Protocol
        self.__dst_factory = dst_factory if dst_factory is not None else Protocol
        self.__src = None
        self.__dst = None

    @property
    def source(self): return self.__src

    @property
    def destination(self): return self.__dst

    async def initialize(self, dest_host, dest_port, orig_host, orig_port):
        # source protocol
        self.__src = self.__src_factory()
        self.__src.add_listener(self)

        # destination protocol
        def _create_destination_protocol():
            p = self.__dst_factory()
            p.add_listener(self)
            return p

        try:
            if dest_host == '':
                dest_host = None

            loop = asyncio.get_event_loop()
            _, self.__dst = await loop.create_connection(_create_destination_protocol, dest_host, dest_port)

        except OSError as exc:
            raise ChannelOpenError(OPEN_CONNECT_FAILED, str(exc)) from None

        return self.__src


    def pause_writing(self, source, *args, **kwargs):
        dst = self.__dst if source == self.__src else self.__src
        dst.pause_reading()

    def resume_writing(self, source, *args, **kwargs):
        dst = self.__dst if source == self.__src else self.__src
        dst.pause_reading()


    def data_received(self, data, datatype=None, source=None, *args, **kwargs):
        if source == self.__src:
            dst = self.__dst
        else:
            dst = self.__src

        # dst = self.__dst if source == self.__src else self.__src
        dst.write(data)


    def eof_received(self, source, *args, **kwargs):
        dst = self.__dst if source == self.__src else self.__src
        dst.write_eof()

