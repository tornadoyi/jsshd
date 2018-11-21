import os
import asyncio

from asyncssh.connection import SSHClient, \
    _validate_version, _validate_algs, load_certificates, \
    getpass, saslprep, find_keysign, load_public_keys, \
    load_default_host_public_keys, load_keypairs, load_default_keypairs, connect_agent,\
    _DEFAULT_REKEY_BYTES, _DEFAULT_REKEY_SECONDS, _DEFAULT_PORT

from .connection import InternalFakeSSHClientConnection



class __FakeInternalClient(SSHClient): pass


class FakeSSHClientConnection(InternalFakeSSHClientConnection):
    def __init__(self, *args, **kwargs):
        super(FakeSSHClientConnection, self).__init__(*args, **kwargs)

    def send_packet(self, pkttype, *args, handler=None):
        #print('DST SEND {}'.format(pkttype))
        try:
            return super(FakeSSHClientConnection, self).send_packet(pkttype, *args, handler=handler)
        except Exception as e:
            print(e)





@asyncio.coroutine
def create_connection(client_factory=None, host=None, port=_DEFAULT_PORT, *,
                      loop=None, tunnel=None, family=0, flags=0,
                      local_addr=None, known_hosts=(), x509_trusted_certs=(),
                      x509_trusted_cert_paths=(),
                      x509_purposes='secureShellServer', username=None,
                      password=None, client_host_keysign=False,
                      client_host_keys=None, client_host=None,
                      client_username=None, client_keys=(), passphrase=None,
                      gss_host=(), gss_delegate_creds=False,
                      agent_path=(), agent_forwarding=False,
                      client_version=(), kex_algs=(), encryption_algs=(),
                      mac_algs=(), compression_algs=(), signature_algs=(),
                      rekey_bytes=_DEFAULT_REKEY_BYTES,
                      rekey_seconds=_DEFAULT_REKEY_SECONDS,
                      connection_wrapper=None):



    if not host: raise Exception('invalid host None')

    def conn_factory():
        """Return an SSH client connection handler"""

        conn = FakeSSHClientConnection(client_factory, loop, client_version,
                                   x509_trusted_certs, x509_trusted_cert_paths,
                                   x509_purposes, kex_algs, encryption_algs,
                                   mac_algs, compression_algs, signature_algs,
                                   rekey_bytes, rekey_seconds, host, port,
                                   known_hosts, username, password,
                                   client_host_keysign, client_host_keys,
                                   client_host, client_username, client_keys,
                                   gss_host, gss_delegate_creds, agent,
                                   agent_path, auth_waiter)

        return conn if connection_wrapper is None else connection_wrapper(conn)

    if not client_factory:
        client_factory = __FakeInternalClient

    if not loop:
        loop = asyncio.get_event_loop()

    client_version = _validate_version(client_version)

    kex_algs, encryption_algs, mac_algs, compression_algs, signature_algs = \
        _validate_algs(kex_algs, encryption_algs, mac_algs, compression_algs,
                       signature_algs, x509_trusted_certs is not None)

    if x509_trusted_certs == ():
        try:
            x509_trusted_certs = load_certificates(
                os.path.join(os.path.expanduser('~'), '.ssh', 'ca-bundle.crt'))
        except OSError:
            pass
    elif x509_trusted_certs is not None:
        x509_trusted_certs = load_certificates(x509_trusted_certs)

    if x509_trusted_cert_paths == ():
        path = os.path.join(os.path.expanduser('~'), '.ssh', 'crt')
        if os.path.isdir(path):
            x509_trusted_cert_paths = [path]
    elif x509_trusted_cert_paths:
        for path in x509_trusted_cert_paths:
            if not os.path.isdir(path):
                raise ValueError('Path not a directory: ' + str(path))

    if username is None:
        username = getpass.getuser()

    username = saslprep(username)

    if client_host_keysign:
        client_host_keysign = find_keysign(client_host_keysign)

        if client_host_keys:
            client_host_keys = load_public_keys(client_host_keys)
        else:
            client_host_keys = load_default_host_public_keys()
    else:
        client_host_keys = load_keypairs(client_host_keys, passphrase)

    if client_username is None:
        client_username = getpass.getuser()

    client_username = saslprep(client_username)

    if gss_host == ():
        gss_host = host

    agent = None

    if agent_path == ():
        agent_path = os.environ.get('SSH_AUTH_SOCK', None)

    if client_keys:
        client_keys = load_keypairs(client_keys, passphrase)
    elif client_keys == ():
        if agent_path:
            agent = yield from connect_agent(agent_path, loop=loop)

            if agent:
                client_keys = yield from agent.get_keys()
            else:
                agent_path = None

        if not client_keys:
            client_keys = load_default_keypairs(passphrase)

    if not agent_forwarding:
        agent_path = None

    auth_waiter = asyncio.Future(loop=loop)

    # pylint: disable=broad-except
    try:
        if tunnel:
            #tunnel_logger = getattr(tunnel, 'logger', logger)
            #tunnel_logger.info('Opening SSH tunnel to %s', (host, port))
            _, conn = yield from tunnel.create_connection(conn_factory, host,
                                                          port)
        else:
            #logger.info('Opening SSH connection to %s', (host, port))
            _, conn = yield from loop.create_connection(conn_factory, host,
                                                        port, family=family,
                                                        flags=flags,
                                                        local_addr=local_addr)
    except Exception:
        if agent:
            agent.close()

        raise

    yield from auth_waiter

    return conn




if __name__ == '__main__':

    async def main():
        conn = await create_connection(None,
                                          '120.131.14.26',
                                          client_keys=[os.path.expanduser('~/.ssh/id_rsa')],
                                          username='root',
                                          known_hosts=None)

        result = await conn.run('ls', check=True)
        #print(result.stdout)

        #conn.close()



    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()