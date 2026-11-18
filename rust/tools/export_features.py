"""Writes features.jsonc (the mod and feature lists of the Rust app) from the tables at the top of
skyblock_config_manager.py, so the two versions stay identical while both exist.

    python rust/tools/export_features.py [--revision N] [--check]

--check only compares: it exits with 1 if features.jsonc no longer matches the Python tables.
"""
import argparse
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "features.jsonc"


def load_python_app():
    try:
        import tkinter  # noqa: F401
    except ImportError:              # the tables don't need Tk; stub it so this runs anywhere
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
    w("// The mods, features and Minecraft versions SkyBlock Config Manager knows about.")
    w("//")
    w("// The app has this file built in, and also downloads the newest copy from the repository, so")
    w("// a change merged here reaches everyone without a new release. Raise \"revision\" with every")
    w("// change: the app only switches to a downloaded copy whose revision is higher than its own.")
    w("// To try changes, put your copy next to the app; it's used instead of the others.")
    w("{")
    w(f'  "format": {data["format"]},')
    w(f'  "revision": {data["revision"]},')
    w("")
    w("  // Minecraft versions in the version menu on the Overview tab, newest first. \"Check for")
    w("  // updates\" looks for mod builds for the version picked.")
    w(f'  "game_versions": {dumps(data["game_versions"])},')
    w("  // Picked until the user chooses another; the feature keys below come from it.")
    w(f'  "default_game_version": {dumps(data["default_game_version"])},')
    w("")
    w("  // Where each mod keeps its config, relative to the config folder (first file found wins).")
    w("  //   dir:  the mod keeps one JSON file per feature in that folder; every file in it is loaded.")
    w("  //   id:   the mod id inside its jar (fabric.mod.json), used to find the installed version.")
    w("  //   slug: the Modrinth project, used by \"Check for updates\".")
    w("  //   curseforge: the CurseForge project id, for mods published there too.")
    w("  // Hypixel SkyBlock mods that aren't listed here are found automatically; their settings can")
    w("  // be browsed and edited, but they aren't compared with other mods.")
    w('  "mods": {')
    names = list(data["mods"])
    for i, name in enumerate(names):
        w(f"    {dumps(name)}: {dumps(data['mods'][name])}" + ("," if i < len(names) - 1 else ""))
    w("  },")
    w("")
    w("  // The feature areas shown on the Priorities tab, in order.")
    w(f'  "areas": {dumps(data["areas"])},')
    w("")
    w("  // Features that more than one mod provides, with each mod's switch for it.")
    w("  //  * A switch is a dotted config key. A list means several switches that all follow together.")
    w("  //  * A key starting with * matches by its ending, for mods whose files nest settings")
    w("  //    differently between versions: \"*spadeGuess\" matches \"spadeGuess\" and \"burrows.spadeGuess\".")
    w("  //  * null means the mod offers the feature but has no single on/off switch; it still competes.")
    w("  //  * A mod only competes if one of its switches is actually in the user's config, so unknown")
    w("  //    keys are harmless.")
    w("  //  * An object means the mod renamed the switch between Minecraft versions: each key is a")
    w("  //    version or a range (\"1.21.5-1.21.10\") and gives the name used there; \"other\" covers the")
    w("  //    rest. The name for the version picked is tried first, then the others.")
    w("  //  * Order matters: an area's default owner is the first mod listed for it, and if the owner")
    w("  //    doesn't offer a feature, the first listed mod that does keeps it.")
    w('  "features": [')
    feats, area = data["features"], None
    for i, f in enumerate(feats):
        if f["area"] != area:
            area = f["area"]
            w(f"    // ── {area} ──")
        mods = list(f["mods"].items())
        w(f'    {{"area": {dumps(f["area"])}, "name": {dumps(f["name"])}, "mods": {{')
        for j, (mod, spec) in enumerate(mods):
            w(f"      {dumps(mod)}: {dumps(spec)}" + ("," if j < len(mods) - 1 else ""))
        w("    }}" + ("," if i < len(feats) - 1 else ""))
    w("  ],")
    w("")
    w("  // Settings nothing else overlaps with, but that should be held at a fixed value.")
    w('  "preferred": [')
    for i, p in enumerate(data["preferred"]):
        w(f"    {dumps(p)}" + ("," if i < len(data["preferred"]) - 1 else ""))
    w("  ],")
    w("")
    w("  // Exact menu names where the tidied-up config key isn't right: {\"Mod\": {\"dotted.key\": \"Name\"}}.")
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
