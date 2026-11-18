"""Checks that the Rust version loads, recommends and saves exactly like the Python version.

    python rust/tools/parity.py <path to scm-dump>

Builds config folders covering every mod and feature in the list (plus JSONC, tabs, one-line files,
named lists, renamed switches, debug settings, broken files and Hypixel SkyBlock mods found in the
mods folder), runs both versions on them, and compares what they load, recommend and save.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_features import load_python_app  # noqa: E402

app = load_python_app()


# ── building config folders ──

def put(tree, segments, value):
    """Sets tree[a][b][c] = value, creating dicts on the way; False if something's in the way."""
    node = tree
    for seg in segments[:-1]:
        child = node.setdefault(seg, {})
        if not isinstance(child, dict):
            return False
        node = child
    if isinstance(node.get(segments[-1]), dict):
        return False
    node[segments[-1]] = value
    return True


EXTRAS = {
    "numbers": {"int": 7, "neg": -12, "zero": 0, "big": 123456789012345678901234567890, "half": 0.5,
                "tiny": 1e-05, "huge": 1e+20, "whole": 100.0, "neg_float": -2.5, "third": 0.3333333333333333},
    "texts": {"plain": "hello", "unicode": "é✓ Ünïcode", "escapes": "line\nnext\t\"quoted\" \\ back", "control": "\u0001x",
              "url": "https://example.com/a//b", "empty": ""},
    "lists": {"ints": [1, 2, 3], "empty": [], "mixed": [1, "two", True, None, {"k": 1}],
              "waypoints": [{"x": i, "y": 64, "z": -i} for i in range(40)]},
    "nested": {"position": {"x": 10, "y": 20}, "color": {"r": 255}, "deep": {"a": {"b": {"c": {"d": True}}}}},
    "empty_obj": {},
    "nothing": None,
    "named": [{"name": "First Thing", "enabled": True, "size": 2}, {"name": 5, "on": False},
              {"name": True, "value": 1}, {"name": None, "x": "y"}],
    "dev": {"debug": {"enabled": False, "commandLogs": True}, "repo": {"user": "someone"}},
    "gui": {"hideGuiInDebugMenu": True, "debugHud": {"extraDebugInfo": False}},
    "settings": {"debugMode": False, "DEVELOPER_MODE": {"value": True}, "devTool": True},
}


def config_for(mod, keys, rng):
    """A config for one mod holding these switches plus every kind of extra value."""
    tree = json.loads(json.dumps(EXTRAS))
    for key in keys:
        segs = key.lstrip("*.").split(".")
        if key.startswith("*"):
            segs = [rng.choice(["features", "misc", "general"])] + segs
        put(tree, segs, rng.random() < 0.5)
    return tree


def odin_config(keys, rng):
    modules = {}
    for key in keys:
        name, _, rest = key.partition(".")
        modules.setdefault(name, {"name": name})
        put(modules[name], rest.split("."), rng.random() < 0.5)
    modules.setdefault("Terminal Solver", {"name": "Terminal Solver"})["Debug"] = False
    modules["Click GUI"] = {"name": "Click GUI", "enabled": True, "Developer Message": True, "color": {"r": 1}}
    return list(modules.values())


def write(path, data, style, rng):
    path.parent.mkdir(parents=True, exist_ok=True)
    if style == "one-line":
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        indent = {"tab": "\t", "4": 4, "2": 2, "3": 3}[style]
        text = json.dumps(data, ensure_ascii=False, indent=indent)
    if path.suffix == ".jsonc" and style != "one-line":
        lines = text.split("\n")
        lines.insert(1, "  // written by the test, with a comment")
        text = "\n".join(lines).replace("\n}", ",\n  /* a block\n comment */\n}", 1) if text.endswith("}") else "\n".join(lines)
    if rng.random() < 0.2:
        text = text.replace("\n", "\r\n")
    raw = text.encode("utf-8")
    if rng.random() < 0.15:
        raw = b"\xef\xbb\xbf" + raw
    path.write_bytes(raw)


def make_jar(path, meta, bundled=(), mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (2026, 1, 1, 0, 0, 0)          # fixed, so each jar's SHA-1 is the same on every run
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("fabric.mod.json", stamp), json.dumps(meta))
        for b in bundled:
            z.writestr(zipfile.ZipInfo(f"META-INF/jars/{b}", stamp), b"jar")
    if mtime:
        os.utime(path, (mtime, mtime))


def keys_by_mod(names_version, skip_mods=()):
    """{mod: [keys]} with the switch names a given Minecraft version uses."""
    out = {}
    for _area, _feature, spec in app.FEATURES:
        for mod, kspec in spec.items():
            if kspec is None or mod in skip_mods:
                continue
            names = app.switch_names(kspec, names_version)[0]
            out.setdefault(mod, []).extend([names] if isinstance(names, str) else names)
    for mod, key, _value in app.PREFERRED:
        out.setdefault(mod, []).append(key)
    return out


def build(root, seed, names_version, skip_mods=()):
    rng = random.Random(seed)
    config, mods_dir = root / "config", root / "mods"
    styles = ["2", "4", "tab", "one-line", "3"]
    for mod, keys in keys_by_mod(names_version, skip_mods).items():
        spec = app.MODS[mod]
        if mod == "Odin":
            write(config / spec["files"][0], odin_config(keys, rng), rng.choice(styles), rng)
        elif spec.get("dir"):
            files = {}
            for key in keys:
                stem, _, rest = key.partition(".")
                put(files.setdefault(stem, json.loads(json.dumps(EXTRAS["numbers"]))), rest.split("."), rng.random() < 0.5)
            files["developer"] = {"auto-rebuild": False, "dev-tools": True}
            files["custom-capes"] = {"developer-capes": True}
            for stem, data in files.items():
                write(config / spec["dir"] / f"{stem}.json", data, rng.choice(styles), rng)
        else:
            data = config_for(mod, keys, rng)
            if mod == "SBO":
                data.setdefault("debug", {})["dianaBurrowGuess"] = True   # a debug copy of a shared switch
            write(config / spec["files"][0], data, rng.choice(styles), rng)
        if spec.get("id"):
            make_jar(mods_dir / f"{spec['id']}-1.{seed}.0.jar", {"id": spec["id"], "version": f"1.{seed}.0+26.1.2", "name": mod})
    # an older copy of one mod: the newer file wins
    make_jar(mods_dir / "skyhanni-old.jar", {"id": "skyhanni", "version": "0.1.0"}, mtime=1_000_000)
    # Hypixel SkyBlock mods the list doesn't have, found on their own
    make_jar(mods_dir / "examplesb.jar", {"id": "examplesb", "name": "Example SB", "version": "2.0",
                                          "description": "Hypixel SkyBlock helper"})
    write(config / "examplesb.json", {"general": {"enabled": True, "debugMode": False}, "radius": 3.5}, "2", rng)
    write(config / "examplesb" / "extra.json", {"a": 1, "b": [1, 2]}, "4", rng)
    write(config / "examplesb" / "cache.json", {"skip": True}, "2", rng)
    (config / "examplesb" / "notes.txt").write_text("not json")
    make_jar(mods_dir / "apiuser.jar", {"id": "apiuser", "name": "Api User", "version": "1.0",
                                        "depends": {"skyblock-api": "*"}})
    write(config / "apiuser-config.json", {"x": True, "y": {"z": 2}}, "tab", rng)
    make_jar(mods_dir / "odin-clone.jar", {"id": "odinclone", "name": "Odin", "version": "1",
                                           "description": "skyblock mod"}, bundled=["hm-api-1.0.jar"])
    write(config / "odinclone.json", {"thing": False}, "2", rng)
    # mods that must not be found: not for Hypixel, and an unrelated "skyblock" survival mod
    make_jar(mods_dir / "sodium.jar", {"id": "sodium", "name": "Sodium", "version": "0.6"})
    write(config / "sodium.json", {"quality": True}, "2", rng)
    make_jar(mods_dir / "islands.jar", {"id": "islands", "name": "Skyblock Islands", "version": "1",
                                        "description": "A sky block survival mod"})
    write(config / "islands.json", {"x": 1}, "2", rng)
    # broken files: a listed mod with unreadable JSON, and one whose file is a bare number
    if "AaronsMod" in skip_mods:
        (config / "aaron-mod.json").write_text('{"broken": [1, 2,,]}')
        make_jar(mods_dir / "aaron.jar", {"id": "aaron-mod", "version": "3.0.1+26.1.2"})
    if "SkyHanni" in skip_mods:
        (config / "skyhanni").mkdir(parents=True, exist_ok=True)
        (config / "skyhanni" / "config.json").write_text("123")


# ── running both versions ──

def py_dump(folder, gv, priority, overrides, resolve, save):
    ws = app.Workspace(priority, overrides, gv)
    ws.load(folder)
    for name, (version, jar) in app.installed_jars(ws.folder.parent / "mods").items():
        ws.mods[name].installed, ws.mods[name].jar = version, jar
    out = dump(ws)
    if resolve:
        out["resolved"] = ws.resolve()
        out["after_resolve"] = dump(ws)["conflicts"]
    if save:
        saved, errors = ws.save()
        out["saved"], out["save_errors"] = saved, len(errors)
    return out


def dump(ws):
    folder = ws.folder
    enc = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    by_mod, by_area, by_feature = ws.conflicts()
    return {
        "mods": [{"name": m.name, "auto": m.auto, "files": [cf.path.relative_to(folder).as_posix() for cf in m.files],
                  "errors": len(m.errors), "settings": len(m.settings), "shared": m.shared, "installed": m.installed,
                  "jar": m.jar.name if m.jar else None} for m in ws.mods.values()],
        "settings": [{"mod": s.mod, "key": s.key, "label": s.label, "value": enc(s.value), "locked": s.locked,
                      "rec": None if s.rec is None else enc(s.rec), "shared": s.shared, "domain": s.domain,
                      "feature": s.feature.key if s.feature else None, "status": app.status_text(s)} for s in ws.settings],
        "features": [{"key": f.key, "winner": f.winner, "live": f.live,
                      "switches": {m: [s.key for s in ss] for m, ss in f.switches.items()}}
                     for f in ws.features if f.switches],
        "shared": [f"{s.mod}|{s.key}" for s in ws.shared],
        "unique": len(ws.unique),
        "choices": ws.choices,
        "owner": ws.owner,
        "conflicts": {"mod": by_mod, "area": by_area, "feature": by_feature},
    }


def rs_dump(exe, folder, gv, priority, overrides, resolve, save):
    args = [exe, str(folder), "--game-version", gv, "--priority", json.dumps(priority), "--overrides", json.dumps(overrides)]
    args += ["--resolve"] * resolve + ["--save"] * save
    return json.loads(subprocess.run(args, check=True, capture_output=True, encoding="utf-8").stdout)


def first_difference(a, b, path="$"):
    if type(a) is not type(b):
        return f"{path}: {a!r} != {b!r}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return f"{path}.{k}: only in {'Rust' if k in b else 'Python'}"
            d = first_difference(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        return None if len(a) == len(b) else f"{path}: {len(a)} items in Python, {len(b)} in Rust"
    return None if a == b else f"{path}: Python {a!r} != Rust {b!r}"


def files_of(root):
    """{relative path: bytes} for every file, with backups named by what they back up."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if ".bak_" in rel:
                rel = rel.split(".bak_")[0] + ".bak"
            out[rel] = p.read_bytes()
    return out


SCENARIOS = [
    # (name, seed, names in the files, version picked, priority, overrides, mods left out)
    ("everything", 1, "26.1.2", "26.1.2", {}, {}, ()),
    ("old names, new version picked", 2, "1.21.8", "26.1.2",
     {"Dungeons": "Skyblocker", "Events": "SBO", "Misc": "NoFrills", "Farming": "Nowhere"},
     {"Dungeons/Dungeon map": "SkyBlockAddons", "Dungeons/Terminal solvers": "Off", "Events/Diana burrow guess": "Nope"}, ()),
    ("old version picked", 3, "1.21.7", "1.21.7", {"GUI/HUD": "SkyBlockAddons", "Inventory": "Firmament"},
     {"Inventory/Inventory buttons": "Firmament", "Misc/Hide lightning": "SkyOcean"}, ()),
    ("some mods missing", 4, "26.1.2", "1.21.11", {"Kuudra": "Odin"}, {}, ("SkyHanni", "Odin", "AaronsMod")),
]


TEXT_CASES = {
    "parse": [[s, False] for s in ["true", " Yes ", "ON", "0", "no", "maybe", ""]]
             + [[s, 5] for s in ["42", " 42 ", "1_000", "-007", "+5", "-0", "1.5", "abc", "1__0", "_1", "", "99999999999999999999999"]]
             + [[s, 0.5] for s in ["1e-5", "3", ".5", "5.", "inf", "nan", "-infinity", "1_0.5", "abc", "1e400", "0.1",
                                   "1e16", "1e15", "123456789.123456789", "-2.50", "1E3", " 7 ", ""]]
             + [[s, [1]] for s in ["[1, 2]", "{}", "[", "  [true]  ", "null"]]
             + [[s, {"a": 1}] for s in ['{"b": [1]}', "[]", "{"]]
             + [[s, "text"] for s in ["  keep  ", "", "é✓"]],
    "fmt": [None, True, False, 0, -12, 0.5, 1e-05, 1e+20, "hello", "x" * 100, "é" * 90, [], {}, [1, "two", None],
            {"k": [1, 2, {"deep": "é"}]}, [{"x": i, "y": 64} for i in range(50)], "line\nnext", 123456789012345678901234567890],
    "words": ["HTMLParser", "abc123Def", "über_cool", "ÄBC", "x-y z", "__init__", "A", "", "123", "ßtraße", "enableTeleportOverlays",
              "DUNGEONS_MAP_DISPLAY", "showOn", "the_end", "a_b_c", "UUIDValue", "FPSDisplay", "x2Y", "camelCASEWord"],
    "debug": ["dev", "debug", "devTool", "debugMode", "DEVELOPER_MODE", "Developer Message", "debugOnlyMessages", "enableDebug",
              "hideGuiInDebugMenu", "debugHud", "extraDebugInfo", "developer-capes", "Dev Size", "device", "devourer", "mode",
              "DEV", "debug_logging", "Debug Mode", "showDebugInfo", "devs", "developers", "", "settings", "dev-tools"],
    "label": [["M", "a", ["enabled"]], ["M", "a.b", ["dungeonMap", "enableMap"]], ["M", "x", ["map", "position", "x"]],
              ["M", "x", ["Map", "Pos", "Y"]], ["M", "x", ["a", "A"]], ["M", "x", ["Some Feature", "value"]],
              ["M", "x", ["gui", "TPS"]], ["M", "x", ["one", "two", "three", "color", "r"]], ["M", "x", ["Waypoints"]]],
}


def check_text(exe):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(TEXT_CASES, f, ensure_ascii=False)
    try:
        rs = json.loads(subprocess.run([exe, "--text-cases", f.name], check=True, capture_output=True, encoding="utf-8").stdout)
    finally:
        os.unlink(f.name)
    enc = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))

    def parse(text, old):
        try:
            return {"ok": enc(app.parse_value(text, old))}
        except ValueError as e:
            return {"error": str(e)}
    norm_err = lambda r: {"error": "Not valid JSON"} if r.get("error", "").startswith("Not valid JSON") else r
    py = {
        "parse": [norm_err(parse(t, o)) for t, o in TEXT_CASES["parse"]],
        "fmt": [app.fmt(v) for v in TEXT_CASES["fmt"]],
        "words": [app.words(s) for s in TEXT_CASES["words"]],
        "debug": [app.is_debug_segment(s) for s in TEXT_CASES["debug"]],
        "label": [app.make_label(m, k, tuple(s)) for m, k, s in TEXT_CASES["label"]],
        "type": [type(o).__name__ for _t, o in TEXT_CASES["parse"]],
    }
    rs["parse"] = [norm_err(r) for r in rs["parse"]]
    diff = first_difference(py, rs)
    print(f"{'ok' if not diff else 'MISMATCH':8} text helpers: {sum(len(v) for v in TEXT_CASES.values())} cases")
    if diff:
        print("         ", diff[:400])
    return 0 if not diff else 1


def check_updates(exe):
    """Both versions' update checks against the same stand-in Modrinth and CurseForge server."""
    import hashlib
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / ".minecraft"
        build(root, 5, "26.1.2")
        hashes = sorted(hashlib.sha1(p.read_bytes()).hexdigest() for p in (root / "mods").glob("*.jar"))
        gv = "26.1.2"

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def reply(self, code, body):
                data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                asked = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["hashes"]
                out = {}
                for i, h in enumerate(asked):
                    if i % 6 == 0:
                        out[h] = {"version_number": "1.5.0", "files": [{"hashes": {"sha1": h}}]}
                    elif i % 6 == 1:
                        out[h] = {"version_number": "9.9.9", "files": [{"hashes": {"sha1": "other"}}]}
                    elif i % 6 == 2:
                        out[h] = {"version_number": "nightly-build", "files": []}
                self.reply(200, out)

            def do_GET(self):
                path = self.path.split("?")[0]
                if path.startswith("/mr/project/"):
                    slug = path.split("/")[3]
                    answers = {"nofrills": (200, [{"version_number": "1.50.0"}]), "skyhanni": (200, []),
                               "skyblocker-liap": (404, {}), "aaron-mod": (500, {}), "odin": (200, "not json"),
                               "firmament": (200, [{"nothing": 1}]), "skyocean": (200, [{"version_number": "0.0.1"}])}
                    self.reply(*answers.get(slug, (200, [{"version_number": "2.0.0"}])))
                elif path == "/cf/936169":
                    self.reply(200, {"files": [
                        {"name": "skyblocker-6.12.0+26.1.2.jar", "versions": [gv, "Fabric"], "uploaded_at": "2026-11-01T00:00:00Z"},
                        {"name": "skyblocker-6.9.0+26.1.2.jar", "versions": [gv, "Fabric"], "uploaded_at": "2026-10-01T00:00:00Z"},
                        {"name": "skyblocker-7.0.0+26.2.jar", "versions": ["26.2", "Fabric"], "uploaded_at": "2026-12-01T00:00:00Z"}]})
                elif path == "/cf/1353380":
                    self.reply(200, {"files": [{"name": "skyocean.jar", "display": "SkyOcean 3.1.4 for 26.1.2",
                                                "versions": [gv, "Fabric"], "uploaded_at": "2026-11-02"}]})
                else:
                    self.reply(404, {})

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
        env.update(SCM_MODRINTH_API=f"{base}/mr", SCM_CFWIDGET=f"{base}/cf")
        saved_env = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            app.API, app.CFWIDGET = f"{base}/mr", f"{base}/cf"
            ws = app.Workspace(None, None, gv)
            ws.load(root / "config")
            for name, (version, jar) in app.installed_jars(ws.folder.parent / "mods").items():
                ws.mods[name].installed, ws.mods[name].jar = version, jar
            jars = {m.name: (m.installed, m.jar) for m in ws.mods.values() if m.jar}
            py = {k: list(v) for k, v in app.update_status(jars, gv).items()}
            rs = json.loads(subprocess.run([exe, str(root / "config"), "--game-version", gv, "--updates"], check=True,
                                           capture_output=True, encoding="utf-8", env=env).stdout)["updates"]
        finally:
            os.environ.clear()
            os.environ.update(saved_env)
            server.shutdown()
    diff = first_difference(py, rs)
    states = sorted({s for _t, s in py.values()})
    print(f"{'ok' if not diff else 'MISMATCH':8} update check: {len(py)} mods ({', '.join(states)})")
    if diff:
        print("         ", diff[:400])
    return 0 if not diff else 1


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
    exe = sys.argv[1]
    failures = check_text(exe) + check_updates(exe)
    for name, seed, names_version, gv, priority, overrides, skip in SCENARIOS:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base" / ".minecraft"
            build(base, seed, names_version, skip)
            py_root, rs_root = Path(tmp) / "py", Path(tmp) / "rs"
            shutil.copytree(base.parent, py_root)
            shutil.copytree(base.parent, rs_root)
            py = py_dump(py_root / ".minecraft" / "config", gv, priority, overrides, True, True)
            rs = rs_dump(exe, rs_root / ".minecraft" / "config", gv, priority, overrides, True, True)
            diff = first_difference(py, rs)
            py_files, rs_files = files_of(py_root), files_of(rs_root)
            file_diff = next((f"{k}: saved file differs" for k in sorted(set(py_files) | set(rs_files))
                              if py_files.get(k) != rs_files.get(k)), None)
            n = len(py["settings"])
            shared = len(py["shared"])
            locked = sum(s["locked"] for s in py["settings"])
            status = "ok" if not (diff or file_diff) else "MISMATCH"
            print(f"{status:8} {name}: {n} settings, {shared} shared, {locked} locked, {py['resolved']} resolved, "
                  f"{len(py['saved'])} files saved, {len(py['mods'])} mods")
            for d in (diff, file_diff):
                if d:
                    print("         ", d[:400])
                    failures += 1
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
