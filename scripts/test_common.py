import sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from utils import common

common.log_ok("This works!")
common.log_err("This is an error!")
print(f"Errors: {common.errors_count}")
