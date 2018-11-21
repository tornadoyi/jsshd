
from collections import OrderedDict
import yaml
from pyplus import importer
from pyplus.collection import qdict



class Config(object):
    def __init__(self, config_path, set_dict={}):
        from jsshd import default_config

        self.__config_path = config_path
        self.__config_dict, \
        self.__config_attrs = Config.__load_config_file(config_path,
                                                        default_config.__file__,
                                                        'Config',
                                                        'Undefined',
                                                        set_dict)

        # init yaml representer
        self.__init_yaml_representer()


    def __getattr__(self, item):
        return qdict.get(self.__config_attrs, item)

    def __str__(self): return yaml.dump(self.__config_dict)


    @staticmethod
    def __load_config_file(config_file_path, default_config_path, config_name, undefined_name, set_dict):
        # load user config
        if config_file_path is None:
            user_cfg = OrderedDict()
        else:
            user_cfg = importer.import_file(config_file_path, OrderedDict())

        # apply set_dict to user config
        for k, v in set_dict.items(): user_cfg[k] = v

        # load default config
        default_config = importer.import_file(default_config_path, OrderedDict())
        config_class = default_config[config_name]
        undefined_class = default_config[undefined_name]

        # merge user config with default config
        config = OrderedDict()
        attrs = qdict()

        for k, v in default_config.items():
            if not isinstance(v, config_class): continue
            v = user_cfg.get(k, v)
            if isinstance(v, undefined_class): raise Exception('Config parse error, Attribute {} must be set'.format(k))
            v = v if not isinstance(v, config_class) else v()
            config[k] = v
            attrs[k.lower()] = v

        return config, attrs



    def __init_yaml_representer(self):
        def _represent_tree(dumper, data):
            value = []
            for item_key, item_value in data.items():
                # find node
                node_key = dumper.represent_data(item_key)
                node_value = dumper.represent_data(item_value)
                value.append((node_key, node_value))

            return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)

        yaml.add_representer(OrderedDict, _represent_tree)


    __repr__ = __str__