import copy
import asyncio
from asyncssh.constants import *

from jsshd.fake import client, server


_SERVER_MESSAGES_PROCESSORS = {
    MSG_KEXINIT: 'internal',
    MSG_NEWKEYS: 'internal',
    MSG_SERVICE_REQUEST: 'internal',
    MSG_USERAUTH_REQUEST: 'user_auth',
    MSG_CHANNEL_OPEN: 'redirect',
    MSG_CHANNEL_REQUEST: 'redirect',
    MSG_CHANNEL_DATA: 'redirect',
    MSG_CHANNEL_CLOSE: 'redirect',
    MSG_CHANNEL_EOF: 'redirect',
    MSG_DISCONNECT: 'redirect',
}

_CLIENT_MESSAGE_PROCESSORS = {
    MSG_GLOBAL_REQUEST: 'internal',
    MSG_CHANNEL_OPEN_CONFIRMATION: 'redirect',
    MSG_CHANNEL_SUCCESS: 'redirect',
    MSG_CHANNEL_WINDOW_ADJUST: 'redirect',
    MSG_CHANNEL_DATA: 'redirect',
    MSG_CHANNEL_REQUEST: 'redirect',
    MSG_CHANNEL_EXTENDED_DATA: 'redirect',
    MSG_CHANNEL_EOF: 'redirect',
    MSG_CHANNEL_CLOSE: 'redirect',
}


class Bridge(object):

    SRC_PACKET_HANDLERS = {}
    DST_PACKET_HANDLERS = {}

    def __init__(self, orig_host, orig_port, server_params, client_params):
        super(Bridge, self).__init__()
        self.__orig_host = orig_host
        self.__orig_port = orig_port
        self.__server_params = copy.deepcopy(server_params)
        self.__client_params = copy.deepcopy(client_params)
        self.__loop = asyncio.get_event_loop()
        self.__src = None
        self.__dst = None


        # set listener
        def connection_wrapper(conn):
            conn.add_listener(self)
            return conn
        self.__server_params['connection_wrapper'] = connection_wrapper
        self.__client_params['connection_wrapper'] = connection_wrapper


    @property
    def source(self): return self.__src

    @property
    def destination(self): return self.__dst

    async def initialize(self):
        await self.__create_fake_server()
        return self.__src


    def connection_made(self, transport, messager):
        src, dst = messager, self.__src if self.__src == messager else self.__dst
        if src == self.__src:
            print('fake server connection_made')
        else:
            print('fake client connection_made')


    def connection_lost(self, exc, messager):
        src, dst = messager, self.__src if self.__src == messager else self.__dst
        if src == self.__src:
            print('fake server connection_lost')
        else:
            print('fake client connection_lost')


    def pause_writing(self, messager): pass

    def resume_writing(self, messager): pass


    def __process_src_packet(self, pkttype, pktid, packet):
        handler = self.SRC_PACKET_HANDLERS.get(pkttype, None)
        if handler is None: raise Exception('Unsupported packet type {}'.format(pkttype))
        return handler(self, pkttype, pktid, packet)


    def __process_dst_packet(self, pkttype, pktid, packet):
        handler = self.DST_PACKET_HANDLERS.get(pkttype, None)
        if handler is None: raise Exception('Unsupported packet type {}'.format(pkttype))
        return handler(self, pkttype, pktid, packet)


    async def __create_fake_server(self):
        self.__src = await server.create_connection(**self.__server_params)

        # set process_packet_callback
        self.__src.process_packet_callback = self.__process_src_packet


    async def __create_fake_client(self):
        self.__dst = await client.create_connection(**self.__client_params)

        # set process_packet_callback
        self.__dst.process_packet_callback = self.__process_dst_packet


# ================================ MESSAGES PROCESSORS ================================ #

    def _process_src_internal(self, *args, **kwargs): return None

    def _process_dst_internal(self, *args, **kwargs): return None

    def _process_src_redirect(self, pkttype, pktid, packet):
        self.__dst.send_packet(pkttype, packet.get_remaining_payload())
        return True

    def _process_dst_redirect(self, pkttype, pktid, packet):
        self.__src.send_packet(pkttype, packet.get_remaining_payload())
        return True

    def _process_src_user_auth(self, pkttype, pktid, packet):
        async def process():
            p = copy.deepcopy(packet)
            self.__client_params['username'] = p.get_string().decode('utf-8')
            try:
                await self.__create_fake_client()
                self.__src.raw_process_packet(pkttype, pktid, packet)
            except Exception as e:
                return

        self.__loop.create_task(process())
        return True




def _init_message_processors():

    def init(tag, messages, handlers):
        for k, v in messages.items():
            f = getattr(Bridge, '{}_{}'.format(tag, v))
            handlers[k] = f

    init('_process_src', _SERVER_MESSAGES_PROCESSORS, Bridge.SRC_PACKET_HANDLERS)
    init('_process_dst', _CLIENT_MESSAGE_PROCESSORS, Bridge.DST_PACKET_HANDLERS)


_init_message_processors()