import setuptools
from grbljogger import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="grbljogger",
    packages=["grbljogger"],
    version=__version__,
    author="Kai Mach",
    author_email="kaiandremach@web.de",
    description="Joystick jogger for GRBL.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Weeesel/grbljogger",
    project_urls={
        "Bug Tracker": "https://github.com/Weeesel/grbljogger/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Linux",
    ],
    python_requires=">=3.6",
    install_requires = [
        'xbox360controller',
        'pyserial',
    ]
)