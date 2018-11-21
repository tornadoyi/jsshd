import os

class Config(object):
    def __init__(self, value): self.__value = value

    def __call__(self, *args, **kwargs): return self.__value

class Undefined(Config):
    def __init__(self): super(Undefined, self).__init__(None)


PORT = Config(8022)


SERVER_HOST_KEYS = Config(os.path.expanduser('~/.ssh/id_rsa'))


CLIENT_KEYS = Config([os.path.expanduser('~/.ssh/id_rsa')])


LOG_FILE_PATH = Config(None)