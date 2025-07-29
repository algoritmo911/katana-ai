from setuptools import setup, find_packages

setup(
    name="katana-ai",
    version="0.2",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "rich",
        "websockets",
        "pytest-asyncio",
        "PyYAML",
        "jinja2",
        "httpx",
    ],
    entry_points={
        "console_scripts": [
            "katana=katana.cli:main",
        ],
    },
)
