"""LameGame Productions' cherrypy slates tool.

Usage: Put tools.lg_slates.on = True in the [global] section in your config file to enable this tool.

tools.lg_slates.storage_type may be specified to change the storage medium (defaults to RamStorage)
"""

import cherrypy
from .common import *
from .tool import SlateTool

cherrypy.tools.lg_slates = SlateTool()

