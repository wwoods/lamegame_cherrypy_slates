"""LameGame Productions' Slate implementation for CherryPy.

We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a Session object bound to
cherrypy.session to store these variables.

Also provides cherrypy.slate[] to retrieve a named slate.

Call cherrypy.session.expire() to force a session to expire.
"""

import binascii
import datetime
import os
import cPickle as pickle
import random
from hashlib import sha1 as sha
import time
import threading
import types
from warnings import warn

import cherrypy
from cherrypy.lib import httputil

from .common import *

missing = object()

class Slate(object): #PY3 , metaclass=cherrypy._AttributeDocstrings):
    """A CherryPy dict-like Slate object (one per request for session state, as well as any number of named slates).

    Writing is accomplished only when set() is called, setdefault() is called, or an item is written (Slate['key'] = 'value').
    """
    
    name = None
    name__doc = """The slate name/ID.  Each unique name corresponds to a unique slate.  Fixation does not apply to slates - for instance, if a slate with the name 'user-testuser' is expired, then its data is erased, but that is still the name of the slate.
    """
    
    timeout = None
    timeout__doc = "Number of minutes after which to delete slate data, or None for no expiration.  The default for named slates is no expiration.  The default for sessions is one hour."

    storage = None
    storage__doc = "Storage instance for this slate"
    
    clean_freq = 60
    clean_freq__doc = "The poll rate for expired slate cleanup in minutes."
 
    def __init__(self, name, timeout=missing):
        """Initializes the Slate, and wipes expired data if necessary.
        Also updates the Slate's Timestamp (preventing it from expiring for
        timeout minutes), and if timeout is not missing and is not equal
        to the stored timeout, will update the timeout record.
        """
        self.name = name
        self._data = {}
        
        if not timeout is missing:
            self.timeout = timeout

        self.storage = Slate.storage_class(self.name, self.timeout)
        log('Slate loaded: {0}'.format(repr(self.storage)))

    @classmethod
    def is_expired(cls, id):
        """Returns True if the given Slate identifier is expired or non-existant."""
        return Slate.storage_class.is_expired(id)

    @classmethod
    def setup(cls, **kwargs):
        """Performs one-time setup for slates"""
        log.enabled = kwargs.pop('debug', log.enabled)

        for k,v in kwargs.items():
            setattr(cls, k, v)
        
        #storage_class must have been passed in kwargs
        cls.storage_class.setup(kwargs.get('storage_conf', {}))

        if cls.clean_freq and not hasattr(cls.storage_class, 'clean_thread'):
            # clean_up is in instancemethod and not a classmethod,
            # so that tool config can be accessed inside the method.
            t = cherrypy.process.plugins.Monitor(
                cherrypy.engine, Slate.storage_class.clean_up, cls.clean_freq * 60,
                name='Slate cleanup')
            t.subscribe()
            cls.storage_class.clean_thread = t
            t.start()
    
    def expire(self):
        """Delete stored session data."""
        self.storage.expire()
    
    def __getitem__(self, key):
        result = self.storage.get(key, missing)
        if result is missing:
            raise KeyError(key)
        return result
    
    def __setitem__(self, key, value):
        self.storage.set(key, value)
    
    def __delitem__(self, key):
        result = self.storage.pop(key, missing)
        if result is missing:
            raise KeyError(key)

    def get(self, key, default=None):
        """Return the value for the specified key, or default"""
        return self.storage.get(key, default)
    
    def pop(self, key, default=None):
        """Remove the specified key and return the corresponding value.
        If key is not found, default is returned.
        """
        return self.storage.pop(key, default)
    
    def update(self, d):
        """D.update(E) -> None.  Update D from E: for k in E: D[k] = E[k]."""
        self.storage.update(d)
    
    def setdefault(self, key, default=None):
        """D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D."""
        return self.storage.setdefault(key, default)
    
    def clear(self):
        """D.clear() -> None.  Remove all items from D."""
        self.storage.clear()
    
    def keys(self):
        """D.keys() -> list of D's keys."""
        return self.storage.keys()
    
    def items(self):
        """D.items() -> list of D's (key, value) pairs, as 2-tuples."""
        return self.storage.items()
    
    def values(self):
        """D.values() -> list of D's values."""
        return self.storage.values()

class SlateStorage(object): #PY3 , metaclass=cherrypy._AttributeDocstring):
    """The base class for slate storage types"""

    name = None
    name__doc = "The slate's name"

    def __init__(self, name, timeout):
        """Initializes storage for a slate.  Should clear data if expired,
        and update timestamp / timeout.
        """
        raise NotImplementedError()

    def set(self, key, value):
        """Sets the given key to the given value"""
        raise NotImplementedError()

    def get(self, key, default):
        """Gets the given key, or if it does not exist, returns default"""
        raise NotImplementedError()
        
    def pop(self, key, default):
        """Deletes and returns the value for the given key, or if it
        does not exist, returns default
        """
        raise NotImplementedError()

    def clear(self):
        """Erases all values.  Override for efficiency."""
        for k in self.keys():
            self.pop(k, None)

    def keys(self):
        """Returns an iterator or list of all keys."""
        raise NotImplementedError()

    def items(self):
        """Returns an iterator or list of all (key,value) pairs."""
        raise NotImplementedError()

    def values(self):
        """Returns an iterator or list of all values."""
        raise NotImplementedError()

    def expire(self):
        """Expire and/or delete the storage for a slate"""
        raise NotImplementedError()

    def update(self, d):
        """for k in d: self[k] = d[k].  Override to make more efficient."""
        for k,v in d.items():
            self.set(k, v)

    def setdefault(self, key, default):
        """Return the value for key.  If key is not set, set self[key] to default, and return default.  Override for efficiency."""
        result = self.get(key, missing)
        if result is missing:
            self.set(key, default)
            result = default
        return result

    @classmethod
    def setup(cls, config):
        """Set up slate storage medium according to passed config"""

    @classmethod
    def clean_up(cls):
        """Clean up expired sessions (timestamp + timeout < present)"""
        raise NotImplementedError()

    @classmethod
    def is_expired(cls, name):
        """Return True if the given slate is expired"""
        raise NotImplementedError()

class RamSlate(SlateStorage):
    
    # Class-level objects. Don't rebind these!
    cache = {}

    def __init__(self, name, timeout):
        self.name = name
        if RamSlate.is_expired(name):
            self.record = self.cache[name] = {}
        else:
            self.record = self.cache.setdefault('name', {})

        self.record['timestamp'] = time.time()
        self.record['timeout'] = timeout
        self.data = self.record.setdefault('data', {})

    def __str__(self):
        return "RAM{0}".format(self.data)

    def __repr__(self):
        return str(self)

    def set(self, key, value):
        self.data[key] = value

    def get(self, key, default):
        return self.data.get(key, default)

    def pop(self, key, default):
        return self.data.pop(key, default)

    def clear(self):
        self.data = self.record['data'] = {}

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()
    
    def expire(self):
        self._expire(self.name)

    @classmethod
    def is_expired(cls, name):
        obj = cls.cache.get(name, None)
        if obj is None:
            return True
        if obj['timestamp'] + obj['timeout'] * 60 < time.time():
            return True
        return False
    
    @classmethod
    def clean_up(cls):
        """Clean up expired sessions."""
        for id in list(cls.cache.keys()):
            if cls.is_expired(id):
                cls._expire(id)
        log('Cleaned expired sessions')

    @classmethod
    def _expire(cls, id):
        try:
            del cls.cache[id]
        except KeyError:
            pass
    
    def __len__(self):
        """Return the number of active sessions."""
        return len(self.cache)

class PymongoSlate(SlateStorage):
    """Storing slates in MongoDb.

    Available params in storage_conf:
        host: Host address
        port: Port to connect with
        db: Database containing slates collection
        collection: Collection containing slates
    """

    conn = None
    conn__doc = "PyMongo collection object"

    def __init__(self, name, timeout):
        self.name = name
        
        core = self.conn.find_one(
            { 'name': self.name }, { '_id': 1, 'time': 1, 'expire': 1 }
            )

        now = datetime.datetime.utcnow()

        if core is None or core['expire'] < now:
            new_dict = {
                'name': self.name
                ,'time': now
                ,'expire': now + datetime.timedelta(minutes=timeout)
                ,'data': {}
                }
            if core is not None:
                new_dict['_id'] = core['_id']
            self.conn.save(new_dict)
            self._id = new_dict['_id']
        else:
            self._id = core['_id']
            half = (core['expire'] - core['time']) // 2
            up_time = core['time'] + half
            if up_time < now:
                updates = {
                    '$set': {
                        'time': now
                        , 'expire': now + datetime.timedelta(minutes=timeout)
                        }
                    }
                self.conn.update({ '_id': self._id }, updates)

    def __str__(self):
        return "PYMONGO{0}".format(self._id)

    def __repr__(self):
        return str(self)

    def set(self, key, value):
        self.conn.update(
            { '_id': self._id }
            , { '$set': { 'data.' + key: pickle.dumps(value).encode('utf-8') } }
            )

    def get(self, key, default):
        doc = self.conn.find_one({ '_id': self._id }, { 'data.' + key: 1 })
        result = doc.get('data', {}).get(key, default)
        if result is not default:
            result = pickle.loads(str(result.decode('utf-8')))
        return result

    def pop(self, key, default):
        result = self.get(key, default)
        self.conn.update({ '_id': self._id }, { '$unset': { 'data.' + key: 1 } })
        return result

    def clear(self):
        self.conn.update({ '_id': self._id }, { '$unset': { 'data': 1 } })

    def keys(self):
        data = self.conn.find_one({ '_id': self._id }, { 'data': 1 })
        return data['data'].keys()

    def items(self):
        data = self.conn.find_one({ '_id': self._id }, { 'data': 1 })
        return data['data'].items()

    def values(self):
        data = self.conn.find_one({ '_id': self._id }, { 'data': 1 })
        return data['data'].values()
    
    def expire(self):
        self.conn.remove(self._id)

    @classmethod
    def setup(cls, conf):
        import pymongo
        c = pymongo.Connection(
          host=conf.get('host', None)
          ,port=conf.get('port', None)
          )
        d = c[conf['db']]
        cls.conn = d[conf['collection']]
        cls.conn.ensure_index([ ('name', 1) ], background=True)
        cls.conn.ensure_index([ ('expire', 1) ], background=True)

    @classmethod
    def is_expired(cls, name):
        doc = cls.conn.find_one({ 'name': name }, { 'expire': 1 })
        if doc is None:
            return True
        if doc['expire'] < datetime.datetime.utcnow():
            return True
        return False

    @classmethod
    def clean_up(cls):
        now = datetime.datetime.utcnow()
        cls.conn.remove({ 'expire': { '$lt': now } })
        log('Cleaned expired sessions')

class Session(Slate):
    """A container that maps session ID's to an underlying slate."""

    id = None
    id__doc = """Session id.  Use Session.get_slate_name(id) to get the name of a slate with the specified id."""

    session_cookie = 'session_id'
    session_cookie__doc = """Name of cookie where session id is stored"""

    timeout=60
    timeout__doc = """Timeout (in minutes) until session expiration"""

    originalid = None
    originalid__doc = """Client-sent identifier for the session slate"""

    def __init__(self, id=None, **kwargs):
        self.timeout = kwargs.pop('session_timeout', self.timeout)
        self.session_cookie = kwargs.get('session_cookie', self.session_cookie)

        self.originalid = id
        self.id = id
        #Check for expired session, and assign new identifier if
        #necessary.
        self._test_id()

        Slate.__init__(self, self.get_slate_name(), timeout=self.timeout)

        #The response cookie is set in init_session(), at the bottom of this
        #file.

    def expire(self):
        """Expires the session both client-side and slate-side"""
        Slate.expire(self)

        one_year = 60 * 60 * 24 * 365
        e = time.time() - one_year
        cherrypy.serving.response.cookie[self.session_cookie]['expires'] = httputil.HTTPDate(e)

    def get_slate_name(self):
        """Returns the slate name for this session id"""
        return 'session-' + self.id

    def _test_id(self):
        """Test if we are expired.  If we are, assign a new id"""
        if self.id is None or self._is_expired():
            while True:
                self.id = self._generate_id()
                if self._is_expired():
                    break
            log('Session {0} expired -> {1}'.format(self.originalid, self.id))

    def _is_expired(self):
        return Slate.is_expired(self.get_slate_name())
        
    def _generate_id(self):
        """Return a new session id."""
        return binascii.hexlify(os.urandom(20)).decode('ascii')
    
def init_session(
    session_path=None
    , session_path_header=None
    , session_domain=None
    , session_secure=False
    , session_persistent=True
    , **kwargs
    ):
    """Initialize session object (using cookies).
    
    storage_type: one of 'ram', 'file', 'postgresql'. This will be used
        to look up the corresponding class in cherrypy.lib.sessions
        globals. For example, 'file' will use the FileSession class.
    path: the 'path' value to stick in the response cookie metadata.
    path_header: if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].
    name: the name of the cookie.
    timeout: the expiration timeout (in minutes) for the stored session data.
        If 'persistent' is True (the default), this is also the timeout
        for the cookie.
    domain: the cookie domain.
    secure: if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).
    clean_freq (minutes): the poll rate for expired session cleanup.
    persistent: if True (the default), the 'timeout' argument will be used
        to expire the cookie. If False, the cookie will not have an expiry,
        and the cookie will be a "session cookie" which expires when the
        browser is closed.
    
    Any additional kwargs will be bound to the new Session instance,
    and may be specific to the storage type. See the subclass of Session
    you're using for more information.
    """
    
    # Guard against running twice
    if hasattr(cherrypy.serving, "session"):
        return
    
    request = cherrypy.serving.request
    name = session_cookie = kwargs.get('session_cookie', Session.session_cookie)
    cookie_timeout = kwargs.get('session_timeout', None)
    
    # Check if request came with a session ID
    id = None
    if session_cookie in request.cookie:
        id = request.cookie[session_cookie].value
        log('ID obtained from request.cookie: %r' % id)
    else:
        log('New session (no cookie)')
    
    # Create and attach a new Session instance to cherrypy.serving.
    # It will possess a reference to (and lock, and lazily load)
    # the requested session data.
    cherrypy.serving.session = sess = Session(id, **kwargs)
    
    if not session_persistent:
        # See http://support.microsoft.com/kb/223799/EN-US/
        # and http://support.mozilla.com/en-US/kb/Cookies
        cookie_timeout = None
    set_response_cookie(path=session_path, path_header=session_path_header
      , name=name
      , timeout=cookie_timeout, domain=session_domain, secure=session_secure)


def set_response_cookie(path=None, path_header=None, name='session_id',
                        timeout=60, domain=None, secure=False):
    """Set a response cookie for the client.
    
    path: the 'path' value to stick in the response cookie metadata.
    path_header: if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].
    name: the name of the cookie.
    timeout: the expiration timeout for the cookie. If 0 or other boolean
        False, no 'expires' param will be set, and the cookie will be a
        "session cookie" which expires when the browser is closed.
    domain: the cookie domain.
    secure: if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).
    """
    # Set response cookie
    cookie = cherrypy.serving.response.cookie
    cookie[name] = cherrypy.serving.session.id
    cookie[name]['path'] = (path or cherrypy.serving.request.headers.get(path_header)
                            or '/')
    
    # We'd like to use the "max-age" param as indicated in
    # http://www.faqs.org/rfcs/rfc2109.html but IE doesn't
    # save it to disk and the session is lost if people close
    # the browser. So we have to use the old "expires" ... sigh ...
##    cookie[name]['max-age'] = timeout * 60
    if timeout:
        e = time.time() + (timeout * 60)
        cookie[name]['expires'] = httputil.HTTPDate(e)
    if domain is not None:
        cookie[name]['domain'] = domain
    if secure:
        cookie[name]['secure'] = 1

