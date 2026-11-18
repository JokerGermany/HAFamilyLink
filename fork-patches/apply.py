#!/usr/bin/env python3
"""Apply the JokerGermany fork changes on top of an upstream checkout.

Usage: python3 fork-patches/apply.py [REPO_ROOT]

1. Copies everything under fork-patches/overlay/ into the repo (1:1).
2. Inserts the Steam router into familylink-playwright/app/main.py using
   anchors instead of a fixed diff, so upstream edits around it don't break it.
3. Inserts fork-patches/readme-notice.md into README.md right below the
   title, keeping the rest of upstream's README as it is.
Idempotent: running it twice changes nothing. Exits non-zero if an anchor
is missing, so the sync workflow stops instead of pushing a broken build.
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent
OVERLAY = HERE / "overlay"
README_NOTICE = HERE / "readme-notice.md"
NOTICE_START = "<!-- fork-notice:start -->"
NOTICE_END = "<!-- fork-notice:end -->"

IMPORT_LINE = "from app.api.steam_routes import router as steam_router"
INCLUDE_LINE = "app.include_router(steam_router)"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def copy_overlay() -> None:
    for src in sorted(OVERLAY.rglob("*")):
        if src.is_file():
            dst = ROOT / src.relative_to(OVERLAY)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"overlay: {dst.relative_to(ROOT)}")


def patch_main() -> None:
    main = ROOT / "familylink-playwright/app/main.py"
    if not main.is_file():
        fail(f"{main} not found")
    lines = main.read_text(encoding="utf-8").splitlines(keepends=True)

    # 1) import: after the last top-level "from app." import
    if not any(l.strip() == IMPORT_LINE for l in lines):
        idx = [i for i, l in enumerate(lines) if l.startswith("from app.")]
        if not idx:
            fail("anchor 'from app.' import not found in main.py")
        lines.insert(idx[-1] + 1, IMPORT_LINE + "\n")
        print("main.py: import added")

    # 2) include_router: right after the closing ")" of "app = FastAPI("
    if not any(l.strip() == INCLUDE_LINE for l in lines):
        start = next((i for i, l in enumerate(lines)
                      if l.startswith("app = FastAPI(")), None)
        if start is None:
            fail("anchor 'app = FastAPI(' not found in main.py")
        depth, end = 0, None
        for i in range(start, len(lines)):
            depth += lines[i].count("(") - lines[i].count(")")
            if depth <= 0:
                end = i
                break
        if end is None:
            fail("could not find end of 'app = FastAPI(...)' block")
        lines.insert(end + 1, INCLUDE_LINE + "\n")
        print("main.py: include_router added")

    main.write_text("".join(lines), encoding="utf-8")


def patch_readme() -> None:
    readme = ROOT / "README.md"
    if not readme.is_file():
        fail(f"{readme} not found")
    text = readme.read_text(encoding="utf-8")
    notice = README_NOTICE.read_text(encoding="utf-8").strip() + "\n"

    # Already there (re-run): replace the old block so edits to the notice apply.
    if NOTICE_START in text and NOTICE_END in text:
        head, rest = text.split(NOTICE_START, 1)
        _, tail = rest.split(NOTICE_END, 1)
        text = head + notice.rstrip("\n") + tail
    else:
        # anchor: the first "# " title line
        lines = text.splitlines(keepends=True)
        idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
        if idx is None:
            fail("anchor '# ' title not found in README.md")
        lines.insert(idx + 1, "\n" + notice)
        text = "".join(lines)
    readme.write_text(text, encoding="utf-8")
    print("README.md: fork notice added")


if __name__ == "__main__":
    copy_overlay()
    patch_main()
    patch_readme()
    print("fork patches applied")
