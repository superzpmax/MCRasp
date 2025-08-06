import os
import sys
import yaml

def resource_path(filename: str) -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, filename)

conf_path = resource_path("conf.yaml")
cosm_path = resource_path(os.path.join("db", "costumize.yaml"))
extensions_path = resource_path("extensions.yaml")
custcolor_path = resource_path(os.path.join("db", "colors.yaml"))
groups_path = resource_path(os.path.join("db", "groups.yaml"))

try:
    with open(conf_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"[WARNING] Could not find {conf_path}. Using empty defaults for conf.")
    conf = {}

try:
    with open(cosm_path, "r", encoding="utf-8") as f:
        cosm = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"[WARNING] Could not find {cosm_path}. Using empty defaults for cosm.")
    cosm = {}
try:
    with open(extensions_path, "r", encoding="utf-8") as f:
        extensions = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"[WARNING] Could not find {extensions_path}. Using empty defaults for extensions.")
    extensions = {}

try:
    with open(groups_path, "r", encoding="utf-8") as f:
        groups = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"[WARNING] Could not find {groups_path}. Using empty defaults for groups.")
    groups = {}

try:
    with open(custcolor_path, "r", encoding="utf-8") as f:
        custcolor = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"[WARNING] Could not find {custcolor_path}. Using empty defaults for groups.")
    custcolor = {}

