import argparse
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "features.jsonc"


def load_python_app():
    try:
        import tkinter
    except ImportError:
        for name in ("tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk", "tkinter.font"):
            sys.modules[name] = types.ModuleType(name)
        sys.modules["tkinter"].Tk = sys.modules["tkinter"].Toplevel = object
        sys.modules["tkinter.ttk"].Frame = object
    sys.path.insert(0, str(ROOT))
    import skyblock_config_manager as app
    return app


def data_of(app, revision):
    return {
        "format": 1,
        "revision": revision,
        "game_versions": list(app.GAME_VERSIONS),
        "default_game_version": app.GAME_VERSION,
        "mods": {name: dict(spec) for name, spec in app.MODS.items()},
        "areas": list(app.AREAS),
        "features": [{"area": a, "name": n, "mods": dict(spec)} for a, n, spec in app.FEATURES],
        "preferred": [{"mod": m, "key": k, "value": v} for m, k, v in app.PREFERRED],
        "labels": {mod: {k: v for (m, k), v in app.LABELS.items() if m == mod}
                   for mod in dict.fromkeys(m for m, _k in app.LABELS)},
    }


def dumps(value):
    return json.dumps(value, ensure_ascii=False)


def render(data):
    out = []
    w = out.append
    w("{")
    w(f'  "format": {data["format"]},')
    w(f'  "revision": {data["revision"]},')
    w(f'  "game_versions": {dumps(data["game_versions"])},')
    w(f'  "default_game_version": {dumps(data["default_game_version"])},')
    w('  "mods": {')
    names = list(data["mods"])
    for i, name in enumerate(names):
        w(f"    {dumps(name)}: {dumps(data['mods'][name])}" + ("," if i < len(names) - 1 else ""))
    w("  },")
    w(f'  "areas": {dumps(data["areas"])},')
    w('  "features": [')
    feats = data["features"]
    for i, f in enumerate(feats):
        mods = list(f["mods"].items())
        w(f'    {{"area": {dumps(f["area"])}, "name": {dumps(f["name"])}, "mods": {{')
        for j, (mod, spec) in enumerate(mods):
            w(f"      {dumps(mod)}: {dumps(spec)}" + ("," if j < len(mods) - 1 else ""))
        w("    }}" + ("," if i < len(feats) - 1 else ""))
    w("  ],")
    w('  "preferred": [')
    for i, p in enumerate(data["preferred"]):
        w(f"    {dumps(p)}" + ("," if i < len(data["preferred"]) - 1 else ""))
    w("  ],")
    w(f'  "labels": {dumps(data["labels"])}')
    w("}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", type=int)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    app = load_python_app()
    current = app.parse_jsonc(OUT.read_text(encoding="utf-8"))[0] if OUT.exists() else None
    revision = args.revision or (current or {}).get("revision", 1)
    data = data_of(app, revision)
    if args.check:
        same = current is not None and {**current, "revision": 0} == {**data, "revision": 0}
        print("features.jsonc matches the Python tables" if same else
              "features.jsonc is out of date: run python rust/tools/export_features.py --revision <next>")
        sys.exit(0 if same else 1)
    text = render(data)
    parsed = app.parse_jsonc(text)[0]
    assert parsed == data, "rendered file doesn't read back as the same data"
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.name}: {len(data['mods'])} mods, {len(data['features'])} features, revision {revision}")


if __name__ == "__main__":
    main()
