from setuptools import setup, find_packages

setup(
    name="katana-cli",
    version="0.0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "katana = katana_cli.cli:main",
        ],
    },
)
