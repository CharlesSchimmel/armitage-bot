#!/usr/bin/env python3

from setup import setup

setup(
        name="armitage-bot",
        version="0.1",
        author="Charles Schimmelpfennig",
        packages=['armitage-bot']
        install_requires=['praw','requests','sqlite3']
        )
