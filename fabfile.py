import os
import smtplib

from fabric.api import env, local, run, settings, abort, cd, execute, prefix

from contextlib import contextmanager as _contextmanager

env.user = os.environ.get('CHECK_EMAILS_SERVER_USER')

env.hosts = [ env.user +'@' + os.environ.get('CHECK_EMAILS_SERVER_IP') ]

env.password = os.environ.get('CHECK_EMAILS_SERVER_PASSWORD')

env.root = '/var/www/html/'

env.git_url = 'https://github.com/sophicservices/'

env.forward_agent = True


def get_virtualenv_root():
    return os.path.join(env.root, 'sophic/')

def get_root_project():
    return os.path.join(get_virtualenv_root(), 'Project/')


        
env.activate = 'source '+ os.path.join(get_virtualenv_root(),'env/bin/activate') + '&& source ' + os.path.join(get_virtualenv_root(),'checkemails_env')

@_contextmanager
def virtualenv():
    with cd(get_virtualenv_root()):
        with prefix(env.activate):
            yield

def install_requirements():
    branch = 'develop'

    with cd(os.path.join(get_virtualenv_root(), 'Python')):
        run('git checkout {}'.format(branch))
        run('pip install -r requirements.txt')


def collect_static():
    """
    Collect static files to the STATIC_ROOT directory.
    """
    with cd(get_root_project()):
        run("python manage.py collectstatic --noinput")


def migrate_database():
    with cd(get_root_project()):
        run("python manage.py makemigrations")
        run("python manage.py migrate")


def git_pull():
    
    branch = 'develop'

    with cd(get_root_project()):
        run('git checkout {}'.format(branch))
        run('git pull origin {}'.format(branch))


def launch_gunicorn():
    with cd(get_root_project()):
        run("sudo /usr/bin/systemctl restart gunicorn_checkemails-dev.service")
        # celery on dev server not done yet
        # run("sudo /usr/bin/systemctl restart checkemails-worker.service")


def update():   
    execute(git_pull)     
    with virtualenv():
        execute(install_requirements)
        execute(collect_static)
        execute(migrate_database)
        execute(launch_gunicorn)