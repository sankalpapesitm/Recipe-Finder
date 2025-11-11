import pathlib, codecs, shutil

root = pathlib.Path("templates")
for path in root.rglob("*.*"):
    raw = path.read_bytes()
    # Detect BOM: UTF-16 LE/BE or UTF-8-BOM
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    else:                             # assume already utf-8 or ANSI-ish
        text = raw.decode("utf-8", errors="replace")
    path.write_text(text, encoding="utf-8")
print("All files rewritten as UTF-8.")
