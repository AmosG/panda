=================
Configuring Email
=================

Getting an SMTP server
======================

Before you configure PANDA you're going to need access to an SMTP server for sending email. There are several ways you can get access to one of these.

Using your own SMTP
-------------------

If you're organization already has an SMTP server then you may be able to use it for PANDA. Note, however, that if you host PANDA on EC2 and your SMTP server is internal to your organization you may not be able to reach it. It's best to discuss this possibility with the IT staff in charge of your email servers.

If you can use your own SMTP server then make sure you have its address, port number, username and password ready so you can fill them in later.

Using SendGrid
--------------

TODO

Using SES
---------

TODO

Using Gmail
-----------

Another possiblity is to use Gmail's SMTP servers for sending email. Note that this solution is somewhat hacky and probably shouldn't be relied on as a permanant solution.

You'll need to `register for a new Gmail <http://www.gmail.com>`_. Do **not** use your primary email account for this, but do register with a real name and contact information.

That's it. To use the Gmail SMTP servers, you'll use the following configuration for PANDA:

* Host: ``smtp.gmail.com``
* Port: ``587``
* User: ``YOUR_NEW_EMAIL_ADDRESS``
* Password: ``YOUR_NEW_PASSWORD``
* Use TLS: ``True``
* From address: ``YOUR_NEW_EMAIL_ADDRESS``

Configuring PANDA
=================

Once you have your SMTP connection details ready. You're ready to configure your PANDA. Visit the settings page at::

    http://localhost:8000/admin/settings

Replace ``localhost:8000`` with your PANDA's domain name.

You'll be prompted to login. If this is you're first time you can use the default username, ``panda@pandaproject.net`` and the default password ``panda``.

Once you've logged you'll see a list of configuration options. In the section titled "Email settings", fill in the details of your SMTP connection and then click "Update Settings".

To test the new connection click the "Home" link at the top of the screen and then the link to "Add" a new User. Fill in your own email address and click Save. You should get an activation email in your inbox!

