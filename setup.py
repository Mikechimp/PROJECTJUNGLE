"""Setup script for PROJECTJUNGLE."""

from setuptools import setup, find_packages

from jungle import __version__

setup(
    name="projectjungle",
    version=__version__,
    description="AI Metal Jam Buddy — generates randomized metal backing tracks for FL Studio",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "jungle=jungle.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
