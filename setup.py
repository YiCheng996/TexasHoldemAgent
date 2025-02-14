from setuptools import setup, find_packages

setup(
    name="texas_holdem_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
        "pyyaml>=6.0.0",
        "sqlalchemy>=2.0.0",
    ],
    python_requires=">=3.9",
) 