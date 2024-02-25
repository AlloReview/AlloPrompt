from setuptools import find_packages, setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name="alloprompt",
    packages=find_packages(include=["alloprompt"]),
    version="0.1.0",
    description="",
    author="AlloBrain",
    install_requires=required,
)
