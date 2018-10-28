#!/usr/bin/env python3

from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='httpsdate',
    version='0.1.0',
    description='Simple and secure system time synchronisation over HTTPS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=[],
    scripts=['httpsdate.py'],
    author='Sebastian Hamann',
    author_email='code@ares-macrotechnology.com',
    url='https://github.com/s-hamann/httpsdate',
    platforms=['Linux'],
    python_requires='>=3.4.3',
    install_requires=['python-prctl >= 1.6.1'],
    license='MIT',
    keywords=['Security', 'Time Synchronization'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: POSIX :: Linux',
        'Topic :: Security',
        'Topic :: System :: Networking :: Time Synchronization',
    ],
)
