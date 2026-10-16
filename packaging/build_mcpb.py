"""Build the Claude Desktop extension (wefact-mcp.mcpb).

Bundles the wefact_mcp package plus all dependencies as Windows/CPython-3.14
wheels into a single .mcpb (a zip with manifest.json at the root).

Usage: python packaging/build_mcpb.py [output.mcpb]
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLATFORM = "win_amd64"
PYTHON_VERSION = "3.14"


def main() -> None:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "wefact-mcp.mcpb").resolve()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = pyproject["project"]["version"]
    deps = pyproject["project"]["dependencies"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        lib = tmp / "stage" / "server" / "lib"
        lib.mkdir(parents=True)

        wheels = tmp / "wheels"
        subprocess.run(
            [sys.executable, "-m", "pip", "download", "--quiet", "--dest", str(wheels),
             "--platform", PLATFORM, "--python-version", PYTHON_VERSION,
             "--only-binary=:all:", *deps],
            check=True,
        )
        for wheel in sorted(wheels.glob("*.whl")):
            with zipfile.ZipFile(wheel) as z:
                z.extractall(lib)

        shutil.copytree(ROOT / "wefact_mcp", lib / "wefact_mcp")
        shutil.copy(ROOT / "packaging" / "main.py", tmp / "stage" / "server" / "main.py")

        manifest = json.loads((ROOT / "packaging" / "manifest.json").read_text())
        manifest["version"] = version
        (tmp / "stage" / "manifest.json").write_text(json.dumps(manifest, indent=2))

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted((tmp / "stage").rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(tmp / "stage"))

    print(f"built {out} (version {version})")


if __name__ == "__main__":
    main()
