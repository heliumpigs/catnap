from distutils.core import setup

setup(name = 'Catnap',
      version = '0.2',
      description = 'A tool for running blackbox tests on REST interfaces',
      author = 'Michael Whidby, Yusuf Simonson',
      url = 'http://github.com/heliumpigs/catnap',
      packages = ['catnap',],
      scripts = ['scripts/nap.py',],
      data_files = [
          ('', ['README', 'LICENSE']),
      ]
     )