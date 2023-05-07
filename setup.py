from setuptools import setup

setup(
    name = 'quick-rest',
    version = '0.0.1',
    description = 'A lightweight toolset for structuring API applications.',
    packages = ['quickrest'],
    package_dir = {'' : 'src'},
    install_requires = [
        'Django>=4.2',
        'pyjwt>=2.6.0',
    ]
)
