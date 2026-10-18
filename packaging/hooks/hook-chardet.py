"""Keep compiled chardet helpers beside their importing extensions on Windows."""
import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("chardet")
package = Path(next(iter(importlib.util.find_spec("chardet").submodule_search_locations)))
# mypyc extensions import sibling helpers from C. Static analysis can infer an
# unqualified name and omit chardet.models._format__mypyc (and pipeline helpers).
# Preserve the wheel's native layout as well as the normal module analysis.
for library in package.rglob("*.pyd"):
    destination = Path("chardet") / library.relative_to(package).parent
    binaries.append((str(library), destination.as_posix()))
