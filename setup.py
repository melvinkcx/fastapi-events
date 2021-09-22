import os

import setuptools


def get_version():
    package_init = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fastapi_events', '__init__.py')
    with open(package_init) as f:
        for line in f:
            if line.startswith('__version__ ='):
                return line.split('=')[1].strip().strip('"\'')


def get_long_description():
    with open("README.md", "r") as fh:
        return fh.read()


setuptools.setup(
    name="fastapi-events",
    version=get_version(),
    author="Melvin Koh",
    author_email="melvinkcx@gmail.com",
    description="Event dispatching library for FastAPI",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/melvinkcx/fastapi-events",
    packages=setuptools.find_packages(exclude=["tests.*"]),
    classifiers={
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9"
    },
    python_requires='>=3.7',
    keywords=["starlette", "fastapi"],
    install_requires=[
        "starlette"
    ],
    extras_require={
        "test": [
            "requests",
            "pytest>=6.2.4",
            "pytest-mock>=3.6.1",
            "pytest-env>=0.6.2",
            "moto[sqs]==2.2",
            "flake8>=3.9.2"
        ],
        "aws": [
            "boto3>=1.14"
        ]
    }
)
