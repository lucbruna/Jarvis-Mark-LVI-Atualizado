# Build with Nuitka for faster startup and smaller distribution.
# Run from project root: .\scripts\build_nuitka.ps1
$ErrorActionPreference = "Stop"
python -m nuitka --standalone --onefile --enable-plugin=pyqt6 `
  --include-package=core --include-package=actions --include-package=plugins `
  --include-package=providers --include-package=memory --include-package=dashboard `
  --output-dir=dist_nuitka main.py
Write-Output "Build complete: dist_nuitka\main.exe"
PY