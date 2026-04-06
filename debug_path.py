import sys
import os
print("Python Executable:", sys.executable)
print("Python Version:", sys.version)
print("Current Directory:", os.getcwd())
print("Path:", sys.path)
try:
    import loguru
    print("Loguru location:", loguru.__file__)
except ImportError as e:
    print("Loguru NOT found:", e)
