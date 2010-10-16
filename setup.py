from setuptools import setup, find_packages
import sys, os

version = '0.0'

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
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      test_suite='test'
      )
