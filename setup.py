from setuptools import setup, find_packages

setup(
    name="katana-ai",
    version="0.2",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "katana=katana.cli:main",
        ],
    },
)
