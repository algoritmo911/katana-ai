from setuptools import setup, find_packages

setup(
    name='KatanaCLI',
    version='0.1',
    packages=['app', 'app.cli', 'app.utils'],
    include_package_data=True,
    install_requires=[
        'click',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'katana-cli = app.cli.katana_cli:cli',
        ],
    },
)
