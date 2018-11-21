
from asyncssh.packet import PacketDecodeError, SSHPacket, UInt32
from asyncssh.constants import *
from asyncssh.misc import  DisconnectError
from asyncssh.connection import SSHConnection, SSHServerConnection, SSHClientConnection
from asyncssh.gss import GSSServer, GSSClient, GSSError

from pyplus.framework import Messager

class FakeSSHConnection(SSHConnection, Messager):

    def __init__(self, *args, **kwargs):
        SSHConnection.__init__(self, *args, **kwargs)
        Messager.__init__(self)

        self.__process_packet_callback = None

    @property
    def process_packet_callback(self): return self.__process_packet_callback

    @process_packet_callback.setter
    def process_packet_callback(self, v): self.__process_packet_callback = v

    def connection_made(self, transport):
        super(FakeSSHConnection, self).connection_made(transport)
        self.notify('connection_made', transport)

    def connection_lost(self, exc):
        super(FakeSSHConnection, self).connection_lost(exc)
        self.notify('connection_lost', exc)

    def pause_writing(self):
        super(FakeSSHConnection, self).pause_writing()
        self.notify('pause_writing')

    def resume_writing(self, *args, **kwargs):
        super(FakeSSHConnection, self).resume_writing()
        self.notify('resume_writing')


    def process_packet(self, pkttype, pktid, packet):
        """Log and process a received packet"""

        if self.__process_packet_callback is not None:
            result = self.__process_packet_callback(pkttype, pktid, packet)
            if result is not None: return result

        return SSHConnection.process_packet(self, pkttype, pktid, packet)


    def raw_process_packet(self, pkttype, pktid, packet):
        return SSHConnection.process_packet(self, pkttype, pktid, packet)



    def _recv_packet(self):
        """Receive the remainder of an SSH packet and process it"""

        rem = 4 + self._pktlen + self._recv_macsize - self._recv_blocksize
        if len(self._inpbuf) < rem:
            return False

        seq = self._recv_seq
        rest = self._inpbuf[:rem-self._recv_macsize]
        mac = self._inpbuf[rem-self._recv_macsize:rem]

        if self._recv_encryption:
            packet = self._recv_encryption.decrypt_packet(seq, self._packet,
                                                          rest, 4, mac)

            if not packet:
                raise DisconnectError(DISC_MAC_ERROR, 'MAC verification failed')
        else:
            packet = self._packet[4:] + rest

        self._inpbuf = self._inpbuf[rem:]
        self._packet = b''

        payload = packet[1:-packet[0]]

        if self._decompressor and (self._auth_complete or
                                   not self._decompress_after_auth):
            payload = self._decompressor.decompress(payload)

        packet = SSHPacket(payload)
        pkttype = packet.get_byte()
        handler = self
        skip_reason = ''
        exc_reason = ''

        if self._kex and MSG_KEX_FIRST <= pkttype <= MSG_KEX_LAST:
            if self._ignore_first_kex: # pragma: no cover
                skip_reason = 'ignored first kex'
                self._ignore_first_kex = False
            else:
                handler = self._kex
        elif (self._auth and
              MSG_USERAUTH_FIRST <= pkttype <= MSG_USERAUTH_LAST):
            handler = self._auth
        elif pkttype > MSG_USERAUTH_LAST and not self._auth_complete:
            skip_reason = 'invalid request before auth complete'
            exc_reason = 'Invalid request before authentication was complete'

        '''
        elif MSG_CHANNEL_FIRST <= pkttype <= MSG_CHANNEL_LAST:
            try:
                recv_chan = packet.get_uint32()
                handler = self._channels[recv_chan]
            except KeyError:
                skip_reason = 'invalid channel number'
                exc_reason = 'Invalid channel number %d received' % recv_chan
            except PacketDecodeError:
                skip_reason = 'incomplete channel request'
                exc_reason = 'Incomplete channel request received'
        '''

        handler.log_received_packet(pkttype, seq, packet, skip_reason)

        if not skip_reason:
            try:
                processed = handler.process_packet(pkttype, seq, packet)
            except PacketDecodeError as exc:
                raise DisconnectError(DISC_PROTOCOL_ERROR, str(exc)) from None

            if not processed:
                self.logger.debug1('Unknown packet type %d received', pkttype)
                self.send_packet(MSG_UNIMPLEMENTED, UInt32(seq))

        if exc_reason:
            raise DisconnectError(DISC_PROTOCOL_ERROR, exc_reason)

        if self._transport:
            self._recv_seq = (seq + 1) & 0xffffffff
            self._recv_handler = self._recv_pkthdr

        return True




InternalFakeSSHServerConnection = type('InternalFakeSSHServerConnection', (FakeSSHConnection, ), dict(SSHServerConnection.__dict__))

def InternalFakeSSHServerConnection__init__(self, server_factory, loop, server_version,
                 x509_trusted_certs, x509_trusted_cert_paths, x509_purposes,
                 kex_algs, encryption_algs, mac_algs, compression_algs,
                 signature_algs, rekey_bytes, rekey_seconds,
                 server_host_keys, known_client_hosts, trust_client_host,
                 authorized_client_keys, gss_host, allow_pty, line_editor,
                 line_history, x11_forwarding, x11_auth_path, agent_forwarding,
                 process_factory, session_factory, session_encoding,
                 session_errors, sftp_factory, allow_scp, window,
                 max_pktsize, login_timeout):

        # modify super call mode
        super(InternalFakeSSHServerConnection, self).__init__(server_factory, loop, server_version,
                         x509_trusted_certs, x509_trusted_cert_paths,
                         x509_purposes, kex_algs, encryption_algs, mac_algs,
                         compression_algs, signature_algs, rekey_bytes,
                         rekey_seconds, server=True)

        self._server_host_keys = server_host_keys
        self._server_host_key_algs = list(server_host_keys.keys())
        self._known_client_hosts = known_client_hosts
        self._trust_client_host = trust_client_host
        self._client_keys = authorized_client_keys
        self._allow_pty = allow_pty
        self._line_editor = line_editor
        self._line_history = line_history
        self._x11_forwarding = x11_forwarding
        self._x11_auth_path = x11_auth_path
        self._agent_forwarding = agent_forwarding
        self._process_factory = process_factory
        self._session_factory = session_factory
        self._session_encoding = session_encoding
        self._session_errors = session_errors
        self._sftp_factory = sftp_factory
        self._allow_scp = allow_scp
        self._window = window
        self._max_pktsize = max_pktsize

        if gss_host:
            try:
                self._gss = GSSServer(gss_host)
                self._gss_mic_auth = True
            except GSSError:
                pass

        if login_timeout:
            self._login_timer = loop.call_later(login_timeout,
                                                self._login_timer_callback)
        else:
            self._login_timer = None

        self._server_host_key = None
        self._key_options = {}
        self._cert_options = None
        self._kbdint_password_auth = False

        self._agent_listener = None


def InternalFakeSSHServerConnection__cleanup(self, exc):
    """Clean up this server connection"""

    if self._agent_listener:
        self._agent_listener.close()
        self._agent_listener = None

    self._cancel_login_timer()

    # modify super call mode
    super(InternalFakeSSHServerConnection, self)._cleanup(exc)




InternalFakeSSHClientConnection = type('_InternalFakeSSHClientConnection', (FakeSSHConnection, ), dict(SSHClientConnection.__dict__))


def InternalFakeSSHClientConnection__init__(self, client_factory, loop, client_version,
             x509_trusted_certs, x509_trusted_cert_paths, x509_purposes,
             kex_algs, encryption_algs, mac_algs, compression_algs,
             signature_algs, rekey_bytes, rekey_seconds, host, port,
             known_hosts, username, password, client_host_keysign,
             client_host_keys, client_host, client_username,
             client_keys, gss_host, gss_delegate_creds, agent,
             agent_path, auth_waiter):

    # modify super call mode
    super(InternalFakeSSHClientConnection, self).__init__(client_factory, loop, client_version,
                     x509_trusted_certs, x509_trusted_cert_paths,
                     x509_purposes, kex_algs, encryption_algs, mac_algs,
                     compression_algs, signature_algs, rekey_bytes,
                     rekey_seconds, server=False)

    self._host = host
    self._port = port
    self._known_hosts = known_hosts
    self._username = username
    self._password = password
    self._client_host_keysign = client_host_keysign
    self._client_host_keys = client_host_keys
    self._client_host = client_host
    self._client_username = client_username
    self._client_keys = client_keys
    self._agent = agent
    self._agent_path = agent_path
    self._auth_waiter = auth_waiter

    if gss_host:
        try:
            self._gss = GSSClient(gss_host, gss_delegate_creds)
            self._gss_mic_auth = True
        except GSSError:
            pass

    self._kbdint_password_auth = False

    self._remote_listeners = {}
    self._dynamic_remote_listeners = {}


def InternalFakeSSHClientConnection__cleanup(self, exc):
    """Clean up this client connection"""

    if self._agent:
        self._agent.close()
        self._agent = None

    if self._remote_listeners:
        for listener in self._remote_listeners.values():
            listener.close()

        self._remote_listeners = {}
        self._dynamic_remote_listeners = {}

    if self._auth_waiter:
        if not self._auth_waiter.cancelled(): # pragma: no branch
            self._auth_waiter.set_exception(exc)

        self._auth_waiter = None

    reason = 'lost: ' + str(exc) if exc else 'closed'
    self.logger.info('Connection %s', reason)

    super(InternalFakeSSHClientConnection, self)._cleanup(exc)





InternalFakeSSHServerConnection.__init__ = InternalFakeSSHServerConnection__init__
InternalFakeSSHServerConnection._cleanup = InternalFakeSSHServerConnection__cleanup


InternalFakeSSHClientConnection.__init__ = InternalFakeSSHClientConnection__init__
InternalFakeSSHClientConnection._cleanup = InternalFakeSSHClientConnection__cleanup