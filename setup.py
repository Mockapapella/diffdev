from setuptools import setup, find_packages

setup(
    name="diffdev",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anthropic",
    ],
    entry_points={
        "console_scripts": [
            "diffdev=src.cli:main",
        ],
    },
)
