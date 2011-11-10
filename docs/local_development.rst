===========================
Local development & testing
===========================

Install basic requirements
==========================

Use the tools appropriate to your operating system to install the following packages. For OSX you can use `Homebrew <https://github.com/mxcl/homebrew>`_. For Ubuntu you can use Apt.

* pip
* virtualenv
* virtualenvwrapper
* PostgreSQL

Setup PANDA
===========

This script will setup the complete application, *except* for Solr. Be sure to read the comments as some steps require opening additional terminals.::

    # Get source and requirements
    git clone git://github.com/pandaproject/panda.git
    cd panda
    mkvirtualenv --no-site-packages panda
    pip install -r requirements.txt

    # Create log directory
    sudo mkdir /var/log/panda
    sudo chown $USER /var/log/panda

    # Enter "panda" when prompted for password
    createuser -d -R -S -P panda
    createdb -O panda panda
    python manage.py syncdb --noinput

    # Start the task queue
    python manage.py celeryd

    # Open another terminal
    workon panda
    python manage.py runserver

Setup Solr
==========

Installing Solr can be tricky and will vary quite a bit depending on your operating system. The following instructions will get you up and running on OSX Lion, using `Homebrew <https://github.com/mxcl/homebrew>`_::

    # Install solr 3.4.0
    brew update
    brew install solr

    # Create Solr home directory
    sudo mkdir /var/solr
    sudo chown $USER /var/solr

    # Ensure you are in the PANDA source directory and your virtualenv is active
    # This command will install all Solr configuration
    fab local_reset_solr

Running Python unit tests
=========================

To run the unit tests start Solr and execute the test runner, like so::

    # Ensure you are in the PANDA source directory and your virtualenv is active
    # You may need to customize the fabfile so it can find your Solr installation.
    fab local_solr

    # Quite a bit of output will be printed to the screen. 
    # Wait until you see something like
    # 2011-11-02 14:15:54.061:INFO::Started SocketConnector@0.0.0.0:8983
    # Then, open another terminal and change to your PANDA source directory.
    workon panda
    python manage.py test redd

Running Javascript unit tests
=============================

Running the Javascript unit tests requires that the application server is running (to render the the JST template map). To run the Javascript tests first start the test server with ``python manage.py runserver``, then open the file ``forest/static/js/SpecRunner.html`` in your browser (e.g. ```file://localhost/Users/onyxfish/src/panda/forest/static/js/SpecRunner.html```.

