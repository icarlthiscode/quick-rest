from setuptools import setup

setup(
    name = 'django-quick-rest',
    version = '0.0.x',
    description = 'A lightweight toolset for structuring API applications.',
    packages = ['quickrest'],
    package_dir = {'' : 'src'},
    install_requires = {
        'Django>=4.1.1',
    }
)
