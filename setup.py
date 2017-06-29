#!/usr/bin/env python
"""
Package setup file for python module
aws_helper
"""
import os
import json
from setuptools import setup


BASE_VERSION = '0.0.1'
METADATA_FILENAME = 'aws_helper/' \
                    'package_metadata.json'
BASEPATH = os.path.dirname(os.path.abspath(__file__))


requires=[
    'boto==2.42.0',
    'boto3==1.4.4',
    'botocore==1.5.4'
]


def readme():
    """
    Get the contents of the README file
    :return:
    """
    possible_filenames = ['README.rst', 'README.md', 'README.txt']
    filename = None
    data = ''
    for filename in possible_filenames:
        if os.path.exists(filename):
            break
    if filename:
        with open(filename) as file_handle:
            data = file_handle.read()
    return data


def scripts():
    """
    Get the scripts in the "scripts" directory

    Returns
    list
        List of filenames
    """
    script_list = []
    if os.path.isdir('scripts'):
        script_list += [
            os.path.join('scripts', f) for f in os.listdir('scripts')
        ]
    return script_list


# Note:
# Replace this code only if you KNOW exactly what you are doing.
# Code to generate a version in setup.py cannot do any of the following:
#    * Run or execute a binary on the system
#    * Use python modules that are not part of the Python standard library
def version(version_file):
    """
    Get the version number based on the BUILD_NUMBER

    Parameters
    ----------
    version_file : str
        The python file to store the version metadata in

    Returns
    -------
    str
        Version string
    """
    build_number = int(os.environ.get('BUILD_NUMBER', '1'))
    setup_version = BASE_VERSION.split('.')
    setup_version[-1] = str(build_number)
    setup_version = '.'.join(setup_version)
    if build_number != 0:
        with open(version_file, 'w') as version_handle:
            json.dump({'version': setup_version}, version_handle)
    elif os.path.exists(version_file):
        with open(version_file) as version_handle:
            setup_version = json.load(version_handle)['version']
    return setup_version


if __name__ == '__main__':
    # We're being run from the command line so call setup with our arguments
    setup(
        author='Phil McCurdy',
        author_email='mccurdypm@mgail.com',
        classifiers=[
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python',
        ],
        description='Short description of this project',
        include_package_data=True,
        install_requires=requires,
        license='MIT',
        long_description=readme(),
        name='aws_helper',
        package_data={
            'aws_helper': ['package_metadata.json']
        },
        packages=['aws_helper'],
        scripts=scripts(),
        url='http://github.com/mccurdypm/'
            'aws_helper',
        version=version(METADATA_FILENAME)
    )
