import os,yaml
class Gconfig:
    def __init__(self) -> None:
        self.init()
        self.__dict__['password'] = self.get('password').encode()
        self.__dict__['salt'] = self.get('salt').encode()
        print('初始化完成')
        
    def init(self) -> None:
        print('初始化配置文件')
        try:
            if not(os.path.exists('config.yaml')):
                raise FileNotFoundError('Config file not found')
            with open('config.yaml') as f:
                config : dict = yaml.safe_load(f)
                print(config)
                if config is None :
                    raise FileNotFoundError('Config file not None')
                if 'password' not in config or \
                    'salt' not in config or \
                    config.get('password') is None or \
                    config.get('salt') is None:
                    f.close()
                    raise KeyError('password or salt not found')
                self.__dict__.update(config)
    
        except FileNotFoundError as e:
            print('Error：',e.__str__())
            print('创建config.yaml')
            with open('config.yaml','w') as f:
                self.__dict__['password'] = input('请键入password(加密用): ')
                self.__dict__['salt'] = os.urandom(16).hex()
                f.write(yaml.safe_dump(self.__dict__))
                print('文件写入成功,请勿泄露妥善保管,请勿修改config.yaml,否则会造成严重后果.')
        except KeyError as e:
            print('Error：',e.__str__())
            self.fixConfig()
    
    def fixConfig(self) -> None:
        print('尝试检查config.yaml')
        with open('config.yaml','r+') as f:
            config:dict = yaml.safe_load(f)
            if config.get('password') is None:
                self.__dict__['password'] = input('请键入password(加密用): ')
            else:
                self.__dict__['password'] = config['password']
            if config.get('salt') is None:
                self.__dict__['salt'] = os.urandom(16).hex()
            else:
                self.__dict__['salt'] = config['salt']
            print(self.__dict__)
            f.seek(0)
            f.write(yaml.safe_dump(self.__dict__))
            
    def get(self,key) -> str:
        return self.__dict__.get(key)