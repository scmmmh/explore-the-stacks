import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = ['pyramid',
            'sqlalchemy',
            'pyramid_tm',
            'zope.sqlalchemy',
            'waitress',
            'decorator',
            'mimeparse',
            'formencode',
            'pyramid_beaker',
            'elasticsearch',
            'lxml',
            'gensim',
            'spacy',
            'kajiki',
            'asset']

setup(name='ExploreTheStacks',
      version='1.3.0',
      description='Book browser using an archive stack exploring UI',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='browsing stacks',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=False,
      test_suite='nose.collector',
      install_requires = requires,
      entry_points = """\
      [paste.app_factory]
      main = ets:main
      [console_scripts]
      ExploreTheStacks = ets.scripts:main
      """,
      )
