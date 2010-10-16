import unittest
import time

import cherrypy
import lamegame_cherrypy_slates

from .common import make_request

class Root(object):
    @cherrypy.expose
    def index(self):
        return "Hello, World!"

    class SessionTests(object):
        @cherrypy.expose
        def get(self, key):
            return cherrypy.session.get(key, 'null')

        @cherrypy.expose
        def get_id(self):
            return cherrypy.session.id

        @cherrypy.expose
        def put(self, key, data):
            cherrypy.session[key] = data
            return 'ok'

        @cherrypy.expose
        def expire(self):
            cherrypy.session.expire()
            return 'ok'

    session = SessionTests()

class SessionRamTest(unittest.TestCase):
    def setUp(self):
        r = Root()
        cherrypy.config.update({
          'tools.lg_slates.on': True
          ,'tools.lg_slates.debug': True
          ,'tools.lg_slates.clean_freq': 0.05 #Fast cleanup for testing (3sec)
          ,'tools.lg_slates.session_timeout': 0.05
          })
        #Ram specific here
        if self.__class__ == SessionRamTest:
            cherrypy.config.update({ 'tools.lg_slates.storage_type': 'ram' })
        cherrypy.tree.mount(r, '/')
        cherrypy.engine.start()

    def tearDown(self):
        cherrypy.engine.stop()

    def test_index(self):
        self.assertEqual(make_request('/'), 'Hello, World!')

    def test_put_expire(self):
        self.assertEqual(make_request('/session/put', { 'key': 'test', 'data': '1234' }), 'ok')
        self.assertEqual(make_request('/session/get', { 'key': 'test' }), '1234')
        self.assertEqual(make_request('/session/expire'), 'ok')
        self.assertEqual(make_request('/session/get', { 'key': 'test' }), 'null')

    def test_timeout_expire(self):
        self.assertEqual(make_request('/session/expire'), 'ok')
        sess_id = make_request('/session/get_id')

        # 3 seconds for session expire
        time.sleep(3.5)

        self.assertNotEqual(make_request('/session/get_id'), sess_id)

class SessionMongoDbTest(SessionRamTest):
    def setUp(self):
        cherrypy.config.update({
          'tools.lg_slates.storage_type': 'pymongo'
          ,'tools.lg_slates.storage_conf': {
            'host': None
            ,'port': None
            ,'db': 'test'
            ,'collection': 'slates'
            }
          })

        SessionRamTest.setUp(self)

