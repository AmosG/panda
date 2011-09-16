# Chicago Tribune News Applications fabfile
# No copying allowed

from fabric.api import *

"""
Base configuration
"""
#name of the deployed site if different from the name of the project
env.site_name = 'panda'

env.user = 'ubuntu'
env.project_name = 'panda'
env.database_password = 'NE3HY2dc16'
env.site_media_prefix = "site_media"
env.admin_media_prefix = "admin_media"
env.path = '/home/%(user)s/src/%(project_name)s' % env
env.log_path = '/home/%(user)s/logs/%(project_name)s' % env
env.env_path = '/home/%(user)s/.virtualenvs/%(project_name)s' % env
env.repo_path = '%(path)s' % env
env.python = 'python2.7'
env.repository_url = "git://github.com/pandaproject/panda.git"

"""
Environments
"""
def production():
    """
    Work on production environment
    """
    env.settings = 'production'
    env.hosts = ['panda.tribapps.com']
    env.s3_bucket = 'media.panda.tribapps.com'
    env.site_domain = 'panda.tribapps.com'    

def staging():
    """
    Work on staging environment
    """
    env.settings = 'staging'
    env.hosts = ['panda.beta.tribapps.com']
    env.s3_bucket = 'media.panda.beta.tribapps.com'
    env.site_domain = 'panda.beta.tribapps.com'    
    
"""
Branches
"""
def stable():
    """
    Work on stable branch.
    """
    env.branch = 'stable'

def master():
    """
    Work on development branch.
    """
    env.branch = 'master'

def branch(branch_name):
    """
    Work on any specified branch.
    """
    env.branch = branch_name
    
"""
Commands - setup
"""
def setup():
    """
    Setup a fresh virtualenv, install everything we need, and fire up the database.
    
    Does NOT perform the functions of deploy().
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    setup_directories()
    setup_virtualenv()
    clone_repo()
    checkout_latest()
    install_requirements()
    destroy_database()
    create_database()
    syncdb()
    deploy_requirements_to_s3()

def setup_directories():
    """
    Create directories necessary for deployment.
    """
    run('mkdir -p %(path)s' % env)
    
def setup_virtualenv():
    """
    Setup a fresh virtualenv.
    """
    run('virtualenv -p %(python)s --no-site-packages %(env_path)s;' % env)
    run('source %(env_path)s/bin/activate;' % env)

def clone_repo():
    """
    Do initial clone of the git repository.
    """
    run('git clone %(repository_url)s %(repo_path)s' % env)

def checkout_latest():
    """
    Pull the latest code on the specified branch.
    """
    run('cd %(repo_path)s; git checkout %(branch)s; git pull origin %(branch)s' % env)

def install_requirements():
    """
    Install the required packages using pip.
    """
    run('source %(env_path)s/bin/activate; pip install -q -r %(repo_path)s/requirements.txt' % env)

def deploy_requirements_to_s3():
    """
    Deploy the admin media to s3.
    """
    with settings(warn_only=True):
        run('s3cmd del --recursive s3://%(s3_bucket)s/%(project_name)s/%(admin_media_prefix)s/' % env)
    
    run('s3cmd -P --guess-mime-type --rexclude-from=%(repo_path)s/s3exclude sync %(env_path)s/src/django/django/contrib/admin/media/ s3://%(s3_bucket)s/%(project_name)s/%(admin_media_prefix)s/' % env)

"""
Commands - deployment
"""
def deploy():
    """
    Deploy the latest version of the site to the server and restart Apache2.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    checkout_latest()
    gzip_assets()
    deploy_to_s3()
    reload_app()
    
def gzip_assets():
    """
    GZips every file in the media directory and places the new file
    in the gzip directory with the same filename.
    """
    run('cd %(repo_path)s; python gzip_assets.py' % env)

def deploy_to_s3():
    """
    Deploy the latest project site media to S3.
    """
    env.media_path = '%(repo_path)s/media/' % env
    run(('s3cmd -P --guess-mime-type --rexclude-from=%(repo_path)s/s3exclude sync %(media_path)s s3://%(s3_bucket)s/%(project_name)s/%(site_media_prefix)s/') % env)

    env.gzip_path = '%(repo_path)s/gzip_media/' % env
    run(('s3cmd -P --add-header=Content-encoding:gzip --guess-mime-type --rexclude-from=%(repo_path)s/s3exclude sync %(gzip_path)s s3://%(s3_bucket)s/%(project_name)s/%(site_media_prefix)s/') % env)
       
def reload_app(): 
    """
    Restart the uwsgi server.
    """
    sudo('service uwsgi restart')
    
"""
Commands - rollback
"""
def rollback(commit_id):
    """
    Rolls back to specified git commit hash or tag.
    
    There is NO guarantee we have committed a valid dataset for an arbitrary
    commit hash.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    checkout_latest()
    git_reset(commit_id)
    gzip_assets()
    deploy_to_s3()
    
"""
Commands - data
"""
def create_database():
    """
    Creates the user and database for this project.
    """
    sudo('echo "CREATE USER %(project_name)s WITH PASSWORD \'%(database_password)s\';" | psql postgres' % env, user='postgres')
    sudo('createdb -O %(project_name)s %(project_name)s' % env, user='postgres')
    
def destroy_database():
    """
    Destroys the user and database for this project.
    
    Will not cause the fab to fail if they do not exist.
    """
    with settings(warn_only=True):
        sudo('dropdb %(project_name)s' % env, user='postgres')
        sudo('dropuser %(project_name)s' % env, user='postgres')
        
def syncdb():
    """
    Sync the Django models to the database.
    """
    run('source %(env_path)s/bin/activate; cd %(repo_path)s; python manage.py syncdb --noinput' % env)
    
def pgpool_down():
    """
    Stop pgpool so that it won't prevent the database from being rebuilt.
    """
    sudo('service pgpool stop')
    
def pgpool_up():
    """
    Start pgpool.
    """
    sudo('service pgpool start')

"""
Deaths, destroyers of worlds
"""
def shiva_the_destroyer():
    """
    Remove all directories, databases, etc. associated with the application.
    """
    with settings(warn_only=True):
        run('rm -Rf %(path)s' % env)
        run('rm -Rf %(log_path)s' % env)
        run('rm -Rf %(env_path)s' % env)
        pgpool_down()
        run('dropdb %(project_name)s' % env)
        run('dropuser %(project_name)s' % env)
        pgpool_up()
        reload_app()
        run('s3cmd del --recursive s3://%(s3_bucket)s/%(project_name)s' % env)

"""
Utility functions (not to be called directly)
"""
def _execute_psql(query):
    """
    Executes a PostgreSQL command using the command line interface.
    """
    env.query = query
    run(('cd %(repo_path)s; psql -q %(project_name)s -c "%(query)s"') % env)
    
def _confirm_branch():
    if (env.settings == 'production' and env.branch != 'stable'):
        answer = prompt("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env, default="Not at all")
        if answer not in ('y','Y','yes','Yes','buzz off','screw you'):
            exit()
