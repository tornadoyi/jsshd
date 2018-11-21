import asyncssh

VALID_EXEC_CMDS = ['ssh-add']

_COMMAND_RUN_MAP = {}

# env is dict: {channel, private_keys=()}
async def run_command(commnad, env):
    # strip command
    strip_chars = ['\n', '\r', ' ']
    cmd = commnad
    for c in strip_chars: cmd = cmd.lstrip(c).rstrip(c)

    # split args
    cmds = cmd.split(' ')

    # check valid cmd
    func = _COMMAND_RUN_MAP.get(cmds[0], None)
    if func is None: return Exception('illegal command {}'.format(commnad))

    # run
    return await func(env, cmds[1:])


async def _run_ssh_add(env, *args):
    # create agent
    chan = env.channel

    # get private key path
    conn = chan.get_connection()

    agent_path = chan.get_agent_path()
    if agent_path is None: return Exception('no available agent')
    agent = await asyncssh.connect_agent(conn)
    if agent is None: return Exception('create agent failed')

    try:

        key_set = set()
        for alg, key in conn._server_host_keys.items(): key_set.add(key._key)

        # add private key
        await agent.add_keys(list(key_set))
    except Exception as e:
        return e
    finally:
        agent.close()

    return 'Identity added success'




for cmd in VALID_EXEC_CMDS:
    cmd_func_name = '_run_' + cmd
    cmd_func_name = cmd_func_name.replace('-', '_')
    _COMMAND_RUN_MAP[cmd] = locals().get(cmd_func_name)