"""Copy a Homebrew Tesseract into a self-contained folder for the macOS app.

    python mac_bundle_tesseract.py /opt/homebrew/bin/tesseract OUT_DIR TESSDATA_DIR

OUT_DIR gets:
    tesseract.bin    the program
    lib/             every library it needs that isn't part of macOS
    tessdata/        English data (+ configs)
    tesseract-run    wrapper the app calls (sets TESSDATA_PREFIX)

Library references are rewritten to @loader_path so nothing depends on Homebrew
being installed on the Mac that runs the app, and every file is re-signed
(ad hoc), which Apple silicon requires after editing a binary.
"""
import shutil
import subprocess
import sys
from pathlib import Path

BREW_LIBS = [Path("/opt/homebrew/lib"), Path("/usr/local/lib")]


def run(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def own_id(f: Path) -> str | None:
    out = run("otool", "-D", str(f)).splitlines()
    return out[1].strip() if len(out) > 1 else None


def deps(f: Path) -> list[str]:
    me = own_id(f)
    refs = [ln.strip().split(" (compatibility")[0] for ln in run("otool", "-L", str(f)).splitlines()[1:]]
    return [r for r in refs if r and r != me]


def rpaths(f: Path) -> list[str]:
    lines = run("otool", "-l", str(f)).splitlines()
    out = []
    for i, ln in enumerate(lines):
        if ln.strip() == "cmd LC_RPATH":
            out.append(lines[i + 2].strip().split("path ", 1)[1].rsplit(" (offset", 1)[0])
    return out


def is_system(ref: str) -> bool:
    return ref.startswith(("/usr/lib/", "/System/"))


def resolve(ref: str, owner: Path, owner_orig: Path, exe_dir: Path) -> Path:
    if ref.startswith("@loader_path/"):
        return (owner_orig.parent / ref.split("/", 1)[1]).resolve()
    if ref.startswith("@executable_path/"):
        return (exe_dir / ref.split("/", 1)[1]).resolve()
    if ref.startswith("@rpath/"):
        name = ref[len("@rpath/"):]
        for r in rpaths(owner):
            r = r.replace("@loader_path", str(owner_orig.parent)).replace("@executable_path", str(exe_dir))
            if (Path(r) / name).exists():
                return (Path(r) / name).resolve()
        for d in BREW_LIBS:
            if (d / name).exists():
                return (d / name).resolve()
        sys.exit(f"Can't find {ref} (needed by {owner_orig})")
    return Path(ref).resolve()


def main() -> None:
    src, out, tessdata = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
    if out.exists():
        shutil.rmtree(out)
    lib = out / "lib"
    lib.mkdir(parents=True)
    exe = out / "tesseract.bin"
    shutil.copy2(src, exe)
    exe.chmod(0o755)

    # (file in our folder, where it came from, prefix its references should use)
    todo = [(exe, src, "@loader_path/lib/")]
    done = []
    while todo:
        f, orig, prefix = todo.pop()
        done.append(f)
        for ref in deps(f):
            if is_system(ref):
                continue
            name = Path(ref).name
            target = lib / name
            if not target.exists():
                real = resolve(ref, f, orig, src.parent)
                shutil.copy2(real, target)
                target.chmod(0o755)
                run("install_name_tool", "-id", f"@loader_path/{name}", str(target))
                todo.append((target, real, "@loader_path/"))
            run("install_name_tool", "-change", ref, prefix + name, str(f))
        for r in rpaths(f):             # no lookups outside the folder
            subprocess.run(["install_name_tool", "-delete_rpath", r, str(f)], capture_output=True)
    for f in done:
        run("codesign", "--force", "--sign", "-", str(f))

    td = out / "tessdata"
    td.mkdir()
    shutil.copy2(tessdata / "eng.traineddata", td)
    if (tessdata / "configs").is_dir():
        shutil.copytree(tessdata / "configs", td / "configs")
    wrapper = out / "tesseract-run"
    wrapper.write_text('#!/bin/sh\nd="${0%/*}"\nTESSDATA_PREFIX="$d/tessdata" exec "$d/tesseract.bin" "$@"\n')
    wrapper.chmod(0o755)

    left = [f"{f.name}: {r}" for f in done for r in deps(f) if not is_system(r) and not r.startswith("@loader_path/")]
    if left:
        sys.exit("Still pointing outside the bundle:\n  " + "\n  ".join(left))
    print(f"Bundled tesseract with {len(done) - 1} libraries into {out}")


if __name__ == "__main__":
    main()
