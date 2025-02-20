from setuptools import setup, find_packages

setup(
    name="texas_holdem_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
        "pyyaml>=6.0.0",
        "sqlalchemy>=2.0.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "websockets>=10.0",
        "python-multipart>=0.0.5",
        "aiofiles>=0.8.0",
    ],
    python_requires=">=3.9",
    author="Your Name",
    description="A Texas Hold'em Poker AI Agent",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
    ],
) 