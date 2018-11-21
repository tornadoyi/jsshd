import sys
import socket
import asyncio
from collections import OrderedDict

from asyncssh import SSHServer, SFTPServer

from asyncssh.connection import \
    _validate_version, _validate_algs, load_certificates, read_authorized_keys, \
    _DEFAULT_LINE_HISTORY, _DEFAULT_WINDOW, _DEFAULT_MAX_PKTSIZE, \
    _DEFAULT_REKEY_BYTES, _DEFAULT_REKEY_SECONDS, _DEFAULT_LOGIN_TIMEOUT

from asyncssh.public_key import load_keypairs
from asyncssh.misc import DisconnectError

from .connection import InternalFakeSSHServerConnection


class __InternalFakeSSHServer(SSHServer):

    def password_auth_supported(self): return False

    def public_key_auth_supported(self): return True

    def validate_public_key(self, username, key): return True

    def connection_requested(self, dest_host, dest_port, orig_host, orig_port): return False

    def session_requested(self): return False



class TransportWrapper(object):

    def __init__(self, channel):
        # transport -> connection -> channel
        self.__chan = channel
        self.__conn = self.__chan.get_connection()
        self.__transport = self.__conn._transport

    def __getattr__(self, item):
        raise Exception('Invalid access {}'.format(item))


    def write(self, *args, **kwargs):
        return self.__chan.write(*args, **kwargs)

    def abort(self):
        self.__conn.close()



class FakeSSHServerConnection(InternalFakeSSHServerConnection):
    def __init__(self, *args, **kwargs):
        super(FakeSSHServerConnection, self).__init__(*args, **kwargs)


    def __getattr__(self, item):
        print(item)


    def connection_made(self, transport, *args, **kwargs):
        self._transport = TransportWrapper(transport)

        sockname = transport.get_extra_info('sockname')
        self._local_addr, self._local_port = sockname[:2]

        peername = transport.get_extra_info('peername')
        self._peer_addr, self._peer_port = peername[:2]

        self._owner = self._protocol_factory()
        self._protocol_factory = None

        # pylint: disable=broad-except
        try:
            self._connection_made()
            self._owner.connection_made(self)
            self._send_version()
        except DisconnectError as exc:
            self._loop.call_soon(self.connection_lost, exc)
        except Exception:
            self._loop.call_soon(self.internal_error, sys.exc_info())

        self.notify('connection_made', transport)







@asyncio.coroutine
def create_connection(server_factory=None, *,
                      loop=None,  server_host_keys=None, passphrase=None,
                      known_client_hosts=None, trust_client_host=False,
                      authorized_client_keys=None, x509_trusted_certs=(),
                      x509_trusted_cert_paths=(), x509_purposes='secureShellClient',
                      gss_host=(), allow_pty=True, line_editor=True,
                      line_history=_DEFAULT_LINE_HISTORY,
                      x11_forwarding=False, x11_auth_path=None,
                      agent_forwarding=True, process_factory=None,
                      session_factory=None, session_encoding='utf-8',
                      session_errors='strict', sftp_factory=None, allow_scp=False,
                      window=_DEFAULT_WINDOW, max_pktsize=_DEFAULT_MAX_PKTSIZE,
                      server_version=(), kex_algs=(), encryption_algs=(),
                      mac_algs=(), compression_algs=(), signature_algs=(),
                      rekey_bytes=_DEFAULT_REKEY_BYTES,
                      rekey_seconds=_DEFAULT_REKEY_SECONDS,
                      login_timeout=_DEFAULT_LOGIN_TIMEOUT,
                      connection_wrapper=None):

    # server_factory
    if not server_factory:
        server_factory = __InternalFakeSSHServer

    if not server_factory:
        server_factory = SSHServer

    if sftp_factory is True:
        sftp_factory = SFTPServer

    if not loop:
        loop = asyncio.get_event_loop()

    server_version = _validate_version(server_version)

    if gss_host == ():
        gss_host = socket.gethostname()

        if '.' not in gss_host:
            gss_host = socket.getfqdn()

    kex_algs, encryption_algs, mac_algs, compression_algs, signature_algs = \
        _validate_algs(kex_algs, encryption_algs, mac_algs, compression_algs,
                       signature_algs, x509_trusted_certs is not None)

    server_keys = load_keypairs(server_host_keys, passphrase)

    if not server_keys and not gss_host:
        raise ValueError('No server host keys provided')

    server_host_keys = OrderedDict()

    for keypair in server_keys:
        for alg in keypair.host_key_algorithms:
            if alg in server_host_keys:
                raise ValueError('Multiple keys of type %s found' %
                                 alg.decode('ascii'))

            server_host_keys[alg] = keypair

    if isinstance(authorized_client_keys, str):
        authorized_client_keys = read_authorized_keys(authorized_client_keys)

    if x509_trusted_certs is not None:
        x509_trusted_certs = load_certificates(x509_trusted_certs)

    conn = FakeSSHServerConnection(server_factory, loop, server_version,
                                x509_trusted_certs, x509_trusted_cert_paths,
                                x509_purposes, kex_algs, encryption_algs,
                                mac_algs, compression_algs, signature_algs,
                                rekey_bytes, rekey_seconds,
                                server_host_keys, known_client_hosts,
                                trust_client_host, authorized_client_keys,
                                gss_host, allow_pty, line_editor,
                                line_history, x11_forwarding, x11_auth_path,
                                agent_forwarding, process_factory,
                                session_factory, session_encoding,
                                session_errors, sftp_factory, allow_scp,
                                window, max_pktsize, login_timeout)

    return conn if connection_wrapper is None else connection_wrapper(conn)