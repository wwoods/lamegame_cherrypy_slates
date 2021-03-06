====================================
LameGame CherryPy Slates (lg_slates)
====================================

About
=====

This module provides partial-update, lockless sessions as well as additional named storage space that may optionally haev an expiration date.  Both sessions and named data stores are implemented as a basic key-value store, where the key must be a string but the value can be any pickle-able python object.

Installation
============

Download the project source and run **python setup.py install** to install.  This project is not entirely python 3.X compatible until PyMongo gains 3.X compatibility.

Dependencies
============

This distribution is supported and tested with python 2.6 and 3.1.

Depends on:

* CherryPy 3 - the web framework that this module is designed for
* (optional) PyMongo - for connectivity to a mongodb database for storage

Example Usage
=============

Set the following in your CherryPy 3 config file:

::

    tools.lg_slates.on: True
    tools.lg_slates.session_timeout: 120    #Use a 2-hour timeout instead of 
                                            #default 1hr
    tools.lg_slates.storage_type: 'pymongo' #For using mongodb
    tools.lg_slates.storage_conf: {
        'host': None              #pymongo host address (None for localhost)
        ,'port': None             #pymongo host port (None for default)
        ,'db': 'test'             #pymongo db to connect to
        ,'collection': 'slates'   #pymongo collection to store slates in
        }

Then make sure that you call **import lg_slates** at some point in your python code before engine.start(), and you should be good to go.

If you'd like to make use of a named slate, for instance to associate user data with an account, do the above setup, and then do something like this in your code::

    import lg_slates
    s = lg_slates.Slate(cherrypy.session['username'])
    s['permanentData'] = True
    val = s.pop('permanentData')

The default behavior for named slates (non-sessions) is to never expire.  However, either a second argument may be passed to **Slate.__init__**, or **tools.lg_slates.timeout** may be set to the desired timeout in minutes.

Testing
=======

Run **python setup.py test**.  Depends on the unittest module.

