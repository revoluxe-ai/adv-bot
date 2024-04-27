import os

PROXY_FILE_PATH = './python_modules/proxies.txt'



class ProxyMaster:
    def get_proxy(self):
        proxies = []
        with open(file_path , 'r') as f:
            lines = f.readlines()
            for line in lines:
                host, port, user, password = line.strip().split(':')
                proxies.append(f'http://{user}:{password}@{host}:{port}')

        return  proxies