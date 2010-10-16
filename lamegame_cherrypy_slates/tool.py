"""LameGame Productions' cherrypy slates tool.

Usage: Put tools.lg_slates.on = True in the [global] section in your config file to enable this tool.

tools.lg_slates.storage_type may be specified to change the storage medium (defaults to RamStorage)
"""

import cherrypy
from .common import *
from . import slates

class SlateTool(cherrypy.Tool):
    """Slate Tool for CherryPy.  Always lazily loaded and explicitly saved.
    """

    storage_class = slates.RamSlate
    storage_class__doc = """The class used for Slate storage"""

    storage_type = None
    storage_type__doc = """The CherryPy configuration for storage_type"""
    
    def __init__(self):
        # slates.init must be bound after headers are read
        cherrypy.Tool.__init__(
          self
          , 'before_request_body'
          , slates.init_session
          , priority=50
          )

    def _setup(self):
        """Hook this tool into cherrypy.request.

        Used to start slate cleanup and hook in slates.init_session

        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        hooks = cherrypy.serving.request.hooks
        
        conf = self._merged_args()
        
        #Check for new storage_type mostly for unit testing (as opposed
        #to the session variable's presence)
        new_storage_type = conf.get('storage_type', 'ram')
        if self.storage_type != new_storage_type:
            if not hasattr(cherrypy, 'session'):
                cherrypy.session = cherrypy._ThreadLocalProxy('session')

            #Find the storage class
            self.storage_type = new_storage_type
            self.storage_class = getattr(slates, self.storage_type.title() + 'Slate')

            # Setup slates and slate storage
            conf['storage_class'] = self.storage_class
            slates.Slate.setup(**conf)
        
        p = conf.pop("priority", None)
        if p is None:
            p = getattr(self.callable, "priority", self._priority)
        
        hooks.attach(self._point, self.callable, priority=p, **conf)
        
