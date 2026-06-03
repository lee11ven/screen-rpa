from __future__ import annotations

import json
import os
import pathlib
import random
import re
import shutil
import time
import uuid
from datetime import datetime
from typing import Any

from app.db.database import db


LOWCODE_BUILTINS: dict[str, Any] = {
    "len": len,
    "range": range,
    "min": min,
    "max": max,
    "sum": sum,
    "str": str,
    "int": int,
    "float": float,
    "dict": dict,
    "list": list,
    "bool": bool,
    "enumerate": enumerate,
    "re": re,
    "time": time,
    "datetime": datetime,
    "os": os,
    "pathlib": pathlib,
    "json": json,
    "uuid": uuid,
    "random": random,
    "shutil": shutil,
    "print": print,
    "db": db,
}
