"""Build script for Nuitka. Run: python scripts/build_nuitka.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = [
    sys.executable, "-m", "nuitka",
    "--standalone", "--onefile",
    "--enable-plugin=pyqt6",
    "--include-package=core", "--include-package=actions",
    "--include-package=plugins", "--include-package=providers",
    "--include-package=memory", "--include-package=dashboard",
    "--output-dir=dist_nuitka",
    str(ROOT / "main.py"),
]
print("Running:", " ".join(args))
subprocess.run(args, check=True, cwd=str(ROOT))
print("Build complete: dist_nuitka/main.exe")
