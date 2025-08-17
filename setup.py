#!/usr/bin/env python3
"""
BigQuery AI Hackathon Project Setup
A comprehensive solution using BigQuery's AI capabilities
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="bigquery-ai-hackathon",
    version="1.0.0",
    author="BigQuery AI Hackathon Team",
    author_email="team@bigquery-ai-hackathon.com",
    description="A comprehensive BigQuery AI solution for the hackathon",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/bigquery-ai-hackathon",
    project_urls={
        "Bug Reports": "https://github.com/your-org/bigquery-ai-hackathon/issues",
        "Source": "https://github.com/your-org/bigquery-ai-hackathon",
        "Documentation": "https://bigquery-ai-hackathon.readthedocs.io/",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database :: Database Engines/Servers",
    ],
    python_requires=">=3.9",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.10.0",
            "flake8>=6.1.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
            "bandit>=1.7.5",
            "safety>=2.3.0",
            "pip-audit>=2.6.0",
        ],
        "docs": [
            "sphinx>=7.2.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
        "performance": [
            "locust>=2.17.0",
            "memory-profiler>=0.61.0",
            "line-profiler>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bigquery-ai=bigquery_ai.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "bigquery_ai": ["*.json", "*.yaml", "*.yml"],
    },
    keywords="bigquery, ai, machine-learning, data-science, google-cloud",
    license="MIT",
    zip_safe=False,
)
