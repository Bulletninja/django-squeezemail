from distutils.core import setup
import re
import os
import sys


name = 'django-squeezemail'
package = 'squeezemail'
description = 'Django mass emailer'
url = 'https://github.com/kronok/django-squeezemail'
author = 'Brandon Jurewicz'
author_email = 'brandonjur@gmail.com'
license = 'MIT'


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("^__version__ = ['\"]([^'\"]+)['\"]", init_py, re.MULTILINE).group(1)


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


def get_package_data(package):
    """
    Return all files under the root package, that are not in a
    package themselves.
    """
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not os.path.exists(os.path.join(dirpath, '__init__.py'))]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename)
                          for filename in filenames])
    return {package: filepaths}


if sys.argv[-1] == 'publish':
    os.system("python setup.py sdist upload")
    args = {'version': get_version(package)}
    print("You probably want to also tag the version now:")
    print("  git tag -a v%(version)s -m 'version v%(version)s'" % args)
    print("  git push --tags")
    sys.exit()


setup(
    name='django-squeezemail',
    version='0.14.1',
    author=author,
    author_email=author_email,
    packages=get_packages(package),
    package_data=get_package_data(package),
    url=url,
    license=license,
    description=description,
    long_description=open('README.rst').read(),
    install_requires=[
        "Django >= 1.9.-",
        "django-content-editor",
        "feincms-cleanse",
        "django-timedeltafield >= 0.7.10",
        "django-ckeditor",
        "celery >= 3.1.22",
        "python-memcached >= 1.57",
        "html2text >= 2016.9.19",
        "django-versatileimagefield <= 1.9"
    ],
)