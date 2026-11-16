"""Metadata only: never load .env or application settings."""
import importlib.metadata
import json
import locale
import os
import platform
import sys
import time

print(json.dumps({"executable":sys.executable,"python":sys.version,"platform":platform.platform(),
    "architecture":platform.machine(),"locale":locale.getlocale(),"timezone":time.tzname,
    "cwd":os.getcwd(),"packages":{p.metadata["Name"]:p.version for p in importlib.metadata.distributions()}},indent=2))
