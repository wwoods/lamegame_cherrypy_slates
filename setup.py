from setuptools import setup, find_packages
import sys, os

try:
    from distutils.command.build_py import build_py_2to3
except ImportError:
    pass

version = '0.0'

#Thanks to http://blog.devork.be/2010/03/using-lib2to3-in-setuppy.html for the
#2to3 code
COMMANDS = {}
if sys.version_info[0] == 3:
    COMMANDS['build_py'] = build_py_2to3

setup(name='lamegame_cherrypy_slates',
      version=version,
      description="LameGame Productions' slates tool for CherryPy",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='cherrypy lamegame session slate',
      author='Walt Woods',
      author_email='woodswalben@gmail.com',
      url='http://www.lamegameproductions.com',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      cmdclass=COMMANDS,
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      test_suite='tests'
      )
