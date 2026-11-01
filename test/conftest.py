"""Test-session setup shared by all test modules."""

import os
import tempfile

# app.main creates FILE_EXPORT_DIR at import time. The default, /output, is not
# writable on a developer machine, so point it at a throwaway directory before
# any test module imports the application.
os.environ.setdefault("FILE_EXPORT_DIR", tempfile.mkdtemp(prefix="fw_export_"))
