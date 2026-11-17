#!/usr/bin/env python3
"""
SkyBlock Config Manager
-----------------------
Finds settings that overlap between Fabric SkyBlock mods, lets you choose which mod
owns each feature area (and each feature), and rewrites the configs so only the owner
keeps it enabled.

    python skyblock_config_manager.py

Python 3.8+, standard library only. Also builds into a portable Windows .exe that needs no
Python installed: run packaging/build_exe.bat (recipe in packaging/SkyBlockConfigManager.spec).
"""
from __future__ import annotations

__version__ = "3.1.0"

import hashlib
import json
import math
import os
import queue
import re
import shutil
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

GAME_VERSION = "26.1.2"
LOADER = "fabric"
MAX_FILE_BYTES = 25 * 1024 * 1024
ALL = "All"
OFF = "Off"                       # a feature override meaning "turn it off in every mod"
FROZEN = bool(getattr(sys, "frozen", False))      # running as the packaged .exe

# ═══════════════════════════════ Edit these to match your pack ═══════════════════════════════
# (The .exe has these built in: after editing, rebuild it with packaging/build_exe.bat.)

# Where each mod keeps its config, relative to the config folder (first file found wins).
#   dir:  the mod keeps one JSON file per feature in that folder; every file in it is loaded.
#   id:   the mod id inside its jar (fabric.mod.json), used to find the installed version.
#   slug: the Modrinth project, used by "Check for updates".
MODS = {
    "NoFrills":       {"files": ["NoFrills/Configuration.json", "Configuration.json"],
                       "id": "nofrills", "slug": "nofrills"},
    "SkyHanni":       {"files": ["skyhanni/config.json", "config.json"],
                       "id": "skyhanni", "slug": "skyhanni"},
    "Skyblocker":     {"files": ["skyblocker.json", "skyblocker_optimized.json"],
                       "id": "skyblocker", "slug": "skyblocker-liap"},
    "AaronsMod":      {"files": ["aaron-mod.json"],
                       "id": "aaron-mod", "slug": "aaron-mod"},
    "SkyBlockAddons": {"files": ["skyblockaddons/configurations.json", "configurations.json"],
                       "id": "skyblockaddons", "slug": "skyblockaddons-unofficial"},
    "SkyOcean":       {"files": ["skyocean/config.jsonc", "skyocean_config.json", "skyocean.json"],
                       "id": "skyocean", "slug": "skyocean"},
    "Firmament":      {"dir": "firmament", "files": ["firmament.json"],
                       "id": "firmament", "slug": "firmament"},
    "Odin":           {"files": ["odin/odin-config.json", "odin-config.json"],
                       "id": "odin", "slug": "odin"},
    "SBO":            {"files": ["SBO/config.jsonc", "config.jsonc"],
                       "id": "sbo", "slug": "skyblock-overhaul"},
}

# The feature areas shown in the Priorities tab, in order.
AREAS = ["Dungeons", "Kuudra", "Slayers", "Farming", "Mining", "Foraging", "Hunting",
         "Fishing", "Events", "Rift", "GUI/HUD", "Inventory", "Misc"]

# Features that more than one mod provides: (area, feature, {mod: its switch(es)}).
#  * A switch is a dotted config key. A list means several switches that all follow together.
#  * A key starting with * matches by its ending, for mods whose files nest settings
#    differently between versions: "*spadeGuess" matches "spadeGuess" and "burrows.spadeGuess".
#  * None means the mod offers the feature but has no single on/off switch; it still competes.
#  * A mod only competes if one of its switches is actually in your config, so unknown
#    keys are harmless.
#  * Order matters: an area's default owner is the first mod listed for it, and if the owner
#    doesn't offer a feature, the first listed mod that does keeps it.
# Keys were read from each mod's 26.1.2 Fabric build.
FEATURES = [
    # ── Dungeons ──
    ("Dungeons", "Dungeon map", {
        "Odin": "Dungeon Map.enabled",
        "Skyblocker": "dungeons.dungeonMap.enableMap"}),
    ("Dungeons", "Terminal solvers", {
        "Odin": "Terminal Solver.enabled",
        "NoFrills": "terminalSolvers.enabled"}),
    ("Dungeons", "Puzzle solvers", {
        "Odin": "Puzzle Solvers.enabled",
        "Skyblocker": ["dungeons.puzzleSolvers.solveTicTacToe", "dungeons.puzzleSolvers.solveThreeWeirdos",
                       "dungeons.puzzleSolvers.creeperSolver", "dungeons.puzzleSolvers.blazeSolver",
                       "dungeons.puzzleSolvers.solveBoulder", "dungeons.puzzleSolvers.solveIceFill",
                       "dungeons.puzzleSolvers.solveSilverfish", "dungeons.puzzleSolvers.solveTrivia",
                       "dungeons.puzzleSolvers.solveTeleportMaze"]}),
    ("Dungeons", "Starred mob highlight", {
        "Odin": "Highlight.enabled",
        "Skyblocker": "dungeons.starredMobGlow",
        "NoFrills": "starredMobHighlight.enabled",
        "SkyHanni": "dungeon.objectHighlighter.starred.highlight"}),
    ("Dungeons", "Livid solver", {
        "Odin": "Livid Solver.enabled",
        "Skyblocker": "dungeons.livid.enableLividColorGlow",
        "NoFrills": "lividSolver.enabled",
        "SkyHanni": "dungeon.lividFinder.enabled"}),
    ("Dungeons", "Spirit leap menu", {
        "Odin": "Leap Menu.enabled",
        "Skyblocker": "dungeons.leapOverlay.enableLeapOverlay",
        "NoFrills": "leapOverlay.enabled",
        "SkyHanni": "dungeon.spiritLeapOverlay.enabled"}),
    ("Dungeons", "Croesus chest helper", {
        "Odin": "Croesus.enabled",
        "Skyblocker": "dungeons.croesusHelper",
        "NoFrills": "croesusSolver.enabled",
        "SkyHanni": "dungeon.chest.croesusOverlay"}),
    ("Dungeons", "Blood camp helper", {
        "Odin": "Blood Camp.enabled",
        "Skyblocker": "dungeons.bloodCampHelper",
        "SkyHanni": "dungeon.bloodCampTimer"}),
    ("Dungeons", "Wither door / key highlight", {
        "Odin": "Door Highlight.enabled",
        "Skyblocker": "dungeons.highlightDoorKeys",
        "NoFrills": "keyHighlight.enabled"}),
    ("Dungeons", "Secret chime", {
        "NoFrills": "secretChime.enabled",
        "SkyHanni": "dungeon.secretChime.enabled"}),
    ("Dungeons", "Wither dragon timers", {
        "Odin": "Wither Dragons.enabled",
        "NoFrills": "witherDragons.enabled",
        "AaronsMod": ["skyblock.m7.dragonSpawnTimers", "skyblock.m7.dragonSpawnNotifications"]}),
    ("Dungeons", "Terracotta timer", {
        "Odin": "Terracotta Timer.enabled",
        "NoFrills": "terracottaTimer.enabled"}),
    ("Dungeons", "Melody message", {
        "Odin": "Melody Message.enabled",
        "NoFrills": "melodyMessage.enabled"}),
    ("Dungeons", "Mimic message", {
        "Odin": "Mimic.enabled",
        "NoFrills": "mimicMessage.enabled"}),
    ("Dungeons", "Auto requeue", {
        "Odin": "Dungeon Queue.enabled",
        "NoFrills": "autoRequeue.enabled"}),
    # ── Kuudra ──
    ("Kuudra", "Supply waypoints", {
        "Odin": "Supply Helper.enabled",
        "Skyblocker": "crimsonIsle.kuudra.supplyWaypoints",
        "NoFrills": "supplyHighlight.enabled"}),
    ("Kuudra", "Pearl waypoints", {
        "Odin": "Pearl Waypoints.enabled",
        "Skyblocker": "crimsonIsle.kuudra.pearlWaypoints"}),
    ("Kuudra", "Ballista build helper", {
        "Odin": "Build Helper.enabled",
        "Skyblocker": "crimsonIsle.kuudra.ballistaBuildWaypoints",
        "NoFrills": "buildPileHighlight.enabled"}),
    ("Kuudra", "Kuudra highlight", {
        "Odin": "Kuudra Info.enabled",
        "Skyblocker": "crimsonIsle.kuudra.kuudraGlow",
        "NoFrills": "kuudraHitbox.enabled"}),
    ("Kuudra", "Fresh tools timer", {
        "Odin": "Fresh Tools.enabled",
        "NoFrills": "freshTimer.enabled"}),
    ("Kuudra", "Fuel / drop-off waypoints", {
        "Skyblocker": "crimsonIsle.kuudra.fuelWaypoints",
        "NoFrills": "dropOffHighlight.enabled"}),
    ("Kuudra", "Vesuvius solver", {
        "Odin": "Vesuvius.enabled",
        "NoFrills": "vesuviusSolver.enabled"}),
    # ── Slayers ──
    ("Slayers", "Boss spawn alert", {
        "Skyblocker": "slayers.bossSpawnAlert",
        "NoFrills": "spawnAlert.enabled"}),
    ("Slayers", "Miniboss spawn alert", {
        "Skyblocker": "slayers.miniBossSpawnAlert",
        "NoFrills": "slayerMinibossAlert.enabled"}),
    ("Slayers", "Boss highlight", {
        "NoFrills": "bossHighlight.enabled",
        "SkyOcean": "*slayer.highlightOwnBoss"}),
    ("Slayers", "Miniboss highlight", {
        "NoFrills": "slayerMinibossHighlight.enabled",
        "SkyOcean": "*slayer.highlightMini"}),
    ("Slayers", "Voidgloom beacon", {
        "Skyblocker": "slayers.endermanSlayer.highlightBeacons",
        "SkyHanni": "slayer.endermen.beacon.highlightBeacon",
        "NoFrills": "beaconTracer.enabled"}),
    ("Slayers", "Nukekubi heads", {
        "Skyblocker": "slayers.endermanSlayer.highlightNukekubiHeads",
        "SkyHanni": "slayer.endermen.highlightNukekebi"}),
    ("Slayers", "Blaze attunement", {
        "Skyblocker": "slayers.blazeSlayer.attunementHighlights",
        "SkyOcean": "*slayer.enableBlazeHighlight"}),
    ("Slayers", "Riftstalker steak alert", {
        "Skyblocker": "slayers.vampireSlayer.enableSteakStakeIndicator",
        "SkyHanni": "slayer.vampire.ownBoss.steakAlert"}),
    ("Slayers", "Boss kill timer", {
        "Skyblocker": "slayers.slainTime",
        "NoFrills": "killTimer.enabled"}),
    # ── Farming ──
    ("Farming", "Pest finder", {
        "SkyHanni": ["garden.pests.pestFinder.showDisplay", "garden.pests.pestFinder.showPlotInWorld"],
        "Skyblocker": "farming.pestHighlighter.enabled",
        "SkyOcean": "*garden.deskPestHighlight"}),
    ("Farming", "Visitor helper", {
        "SkyHanni": "garden.visitors.shoppingList.enabled",
        "Skyblocker": "farming.visitorHelper.enabled"}),
    ("Farming", "Glowing mushrooms", {
        "SkyHanni": "misc.glowingMushroomHighlighter.enabled",
        "Skyblocker": "otherLocations.barn.enableGlowingMushroomHelper",
        "NoFrills": "glowingMushroom.enabled"}),
    # ── Mining ──
    ("Mining", "Metal detector solver", {
        "SkyHanni": "mining.metalDetector.metalDetectorSolver",
        "Skyblocker": "mining.crystalHollows.metalDetectorHelper"}),
    ("Mining", "Fossil solver", {
        "SkyHanni": "mining.fossilExcavator.solver.enabled",
        "Skyblocker": "mining.glacite.fossilSolver"}),
    ("Mining", "Corpse finder", {
        "Skyblocker": "mining.glacite.enableCorpseFinder",
        "NoFrills": "corpseHighlight.enabled",
        "SkyOcean": "*mineshaft.corpseWaypoint"}),
    ("Mining", "Corpse profit tracker", {
        "SkyHanni": "mining.glaciteMineshaft.corpseTracker.enabled",
        "Skyblocker": "mining.glacite.enableCorpseProfitTracker"}),
    ("Mining", "Commission highlight", {
        "SkyHanni": "mining.highlightCommissionMobs",
        "Skyblocker": "mining.commissionHighlight",
        "NoFrills": "commissionHighlight.enabled"}),
    ("Mining", "Puzzler solver", {
        "Skyblocker": "mining.dwarvenMines.solvePuzzler",
        "SkyOcean": "*mining.puzzlerSolver"}),
    ("Mining", "Fetchur solver", {
        "Skyblocker": "mining.dwarvenMines.solveFetchur",
        "SkyOcean": "*mining.fetchurHelper"}),
    ("Mining", "Mineshaft announce", {
        "NoFrills": "shaftAnnounce.enabled",
        "SkyOcean": "*mineshaft.shaftAnnouncement"}),
    ("Mining", "Ender node highlight", {
        "Skyblocker": "otherLocations.end.enableEnderNodeHelper",
        "NoFrills": "endNodeHighlight.enabled"}),
    # ── Foraging ──
    ("Foraging", "Moonglade beacon solver", {
        "SkyHanni": "foraging.foragingBeacon.enabled",
        "Skyblocker": "foraging.moongladeMarsh.enableTunerSolver",
        "NoFrills": "beaconTuningSolver.enabled"}),
    ("Foraging", "Mute phantoms", {
        "SkyHanni": "foraging.mutePhantoms",
        "SkyOcean": "*galatea.muteThePhantoms"}),
    # ── Hunting ──
    ("Hunting", "Shard tracker", {
        "SkyHanni": "hunting.shardTracker.enabled",
        "NoFrills": "shardTracker.enabled"}),
    ("Hunting", "Lasso alert", {
        "SkyHanni": "hunting.lassoDisplay",
        "NoFrills": "lassoAlert.enabled"}),
    ("Hunting", "Invisibug highlight", {
        "Skyblocker": "hunting.moongladeMobs.highlightInvisibug",
        "NoFrills": "invisibugHighlight.enabled"}),
    # ── Fishing ──
    ("Fishing", "Bobber timer", {
        "SkyHanni": "fishing.bobberTimer.enabled",
        "SkyOcean": "*fishing.bobberTime",
        "SBO": "*bobberOverlay"}),
    ("Fishing", "Hide other players' bobbers", {
        "Skyblocker": "helpers.fishing.hideOtherPlayersRods",
        "SkyOcean": "*fishing.hideOtherBobbers"}),
    ("Fishing", "Lava replacement", {
        "SkyHanni": "fishing.lavaReplacement.enabled",
        "SkyOcean": "*fishing.lavaReplacement"}),
    ("Fishing", "Fishing hook display", {
        "SkyHanni": "fishing.fishingHookDisplay.enabled",
        "Skyblocker": "helpers.fishing.enableFishingHelper"}),
    # ── Events ──
    ("Events", "Diana burrow guess", {
        "SBO": "*spadeGuess",
        "SkyHanni": "event.diana.guess",
        "Skyblocker": "helpers.mythologicalRitual.enableMythologicalRitualHelper",
        "Firmament": "diana.ancestral-spade",
        "NoFrills": "dianaSolver.enabled"}),
    ("Events", "Diana arrow guess", {
        "SBO": "*arrowGuess",
        "SkyHanni": "event.diana.guessFromArrow"}),
    ("Events", "Nearby burrow detection", {
        "SBO": "*closeBurrowDetection",
        "SkyHanni": "event.diana.burrowsNearbyDetection"}),
    ("Events", "Nearest warp hint", {
        "SBO": "*showTitleWhenWarpAvailable",
        "SkyHanni": "event.diana.burrowNearestWarp"}),
    ("Events", "Rare mob sharing", {
        "SBO": "*shareRareMob",
        "SkyHanni": "event.diana.rareMobsSharing.enabled"}),
    ("Events", "Rare mob highlight", {
        "SBO": "*highlightRareMobs",
        "SkyHanni": "event.diana.highlightRareMobs"}),
    ("Events", "Mute bugged spade sounds", {
        "SBO": "*muteBuggedSpadeSounds",
        "SkyHanni": "event.diana.muteBuggedSpade"}),
    ("Events", "Chocolate egg finder", {
        "SkyHanni": "event.hoppityEggs.waypoints.enabled",
        "Skyblocker": "helpers.chocolateFactory.enableEggFinder",
        "NoFrills": "hoppitySolver.enabled"}),
    ("Events", "Chocolate factory helper", {
        "SkyHanni": "inventory.chocolateFactory.enabled",
        "Skyblocker": "helpers.chocolateFactory.enableChocolateFactoryHelper"}),
    ("Events", "Time tower reminder", {
        "SkyHanni": "inventory.chocolateFactory.timeTowerReminder",
        "Skyblocker": "helpers.chocolateFactory.enableTimeTowerReminder"}),
    # ── Rift ──
    ("Rift", "Enigma soul waypoints", {
        "SkyHanni": "rift.enigmaSoulWaypoints.enabled",
        "Skyblocker": "otherLocations.rift.enigmaSoulWaypoints"}),
    # ── GUI/HUD ──
    ("GUI/HUD", "Custom tab list", {
        "SkyHanni": "gui.compactTabList.enabled",
        "Skyblocker": "uiAndVisuals.tabHud.tabHudEnabled"}),
    ("GUI/HUD", "TPS display", {
        "SkyHanni": "gui.tpsDisplay",
        "AaronsMod": "uiAndVisuals.tpsHud.enableTpsHud"}),
    ("GUI/HUD", "Health / mana bars", {
        "Skyblocker": "uiAndVisuals.bars.enableBars",
        "Odin": "Player Display.enabled"}),
    ("GUI/HUD", "Item ability cooldowns", {
        "SkyHanni": "inventory.itemAbilities.itemAbilityCooldown",
        "Skyblocker": "uiAndVisuals.itemCooldown.enableItemCooldowns"}),
    ("GUI/HUD", "Quiver display", {
        "SkyHanni": "combat.quiverConfig.quiverDisplay.enabled",
        "Odin": "Quiver Display.enabled"}),
    ("GUI/HUD", "Held item position", {
        "NoFrills": "viewmodel.enabled",
        "AaronsMod": "itemModel.enableItemModelCustomization"}),
    # ── Inventory ──
    ("Inventory", "Inventory buttons", {
        "Firmament": None,
        "NoFrills": "inventoryButtons.enabled",
        "SkyOcean": "*inventory.inventoryButtons"}),
    ("Inventory", "Keep cursor position", {
        "Firmament": "save-cursor-position.enable",
        "Odin": "No Cursor Reset.enabled",
        "NoFrills": "noCursorReset.enabled",
        "AaronsMod": "refinements.input.dontResetCursorPosition"}),
    ("Inventory", "Anvil helper", {
        "SkyHanni": "inventory.anvilCombineHelper",
        "Skyblocker": "helpers.enableAnvilHelper",
        "NoFrills": "anvilHelper.enabled",
        "SkyOcean": "*misc.anvilHelper"}),
    ("Inventory", "Experiment solvers", {
        "Skyblocker": ["helpers.experiments.enableChronomatronSolver",
                       "helpers.experiments.enableSuperpairsSolver",
                       "helpers.experiments.enableUltrasequencerSolver"],
        "SkyHanni": "inventory.experimentationTable.superpairs.highlightPairs",
        "NoFrills": "experimentSolver.enabled"}),
    ("Inventory", "Wardrobe overlay", {
        "SkyHanni": "inventory.customWardrobe.enabled",
        "Skyblocker": "helpers.enableWardrobeHelper"}),
    ("Inventory", "Price tooltips", {
        "Skyblocker": ["general.itemTooltip.enableLowestBIN", "general.itemTooltip.enableAvgBIN",
                       "general.itemTooltip.enableBazaarPrice"],
        "NoFrills": "priceTooltips.enabled"}),
    # ── Misc ──
    ("Misc", "Etherwarp overlay", {
        "Odin": "Etherwarp.enabled",
        "Firmament": "etherwarp-overlay.etherwarp-overlay",
        "NoFrills": "etherwarpOverlay.enabled",
        "Skyblocker": "uiAndVisuals.teleportOverlay.enableTeleportOverlays"}),
    ("Misc", "Auto sprint", {
        "Odin": "Auto Sprint.enabled",
        "NoFrills": "autoSprint.enabled"}),
    ("Misc", "Wardrobe keybinds", {
        "Odin": "Wardrobe Keybinds.enabled",
        "NoFrills": "wardrobeKeybinds.enabled"}),
    ("Misc", "Loadout keybinds", {
        "Odin": "Loadout Keybinds.enabled",
        "NoFrills": "loadoutKeybinds.enabled"}),
    ("Misc", "Command keybinds", {
        "Odin": "Command Keybinds.enabled",
        "NoFrills": "commandKeybinds.enabled"}),
    ("Misc", "Party chat commands", {
        "Odin": "Chat Commands.enabled",
        "NoFrills": "partyCommands.enabled"}),
    ("Misc", "Chat waypoints", {
        "Skyblocker": "uiAndVisuals.waypoints.enableChatWaypoints",
        "NoFrills": "chatWaypoints.enabled"}),
    ("Misc", "Hide lightning", {
        "AaronsMod": "uiAndVisuals.world.hideLightning",
        "SkyOcean": "*environmental.hideLightning"}),
]

# Settings nothing else overlaps with, but that you want held at a fixed value: (mod, key, value).
PREFERRED = [
    ("Firmament",  "inventory-buttons-config.hover-text", True),
    ("Firmament",  "inventory-buttons-config.only-inv",   False),
    ("Skyblocker", "quickNav.enableQuickNav",             True),
]

# Exact menu names where the tidied-up config key isn't right: {("Mod", "dotted.key"): "Name"}.
LABELS: dict = {}

# ═════════════════════════════════════════ Helpers ═══════════════════════════════════════════

HOME_PREFS = Path.home() / ".skyblock_config_manager.json"
PORTABLE_PREFS = "skyblock_config_manager.settings.json"
OLD_AREA_NAMES = {"Garden": "Farming", "Diana": "Events", "Etherwarp": "Misc"}


def renamed_area_key(key):
    """'Garden/Pest finder' -> 'Farming/Pest finder' for overrides saved by older versions."""
    for old, new in OLD_AREA_NAMES.items():
        if key.startswith(old + "/"):
            return new + key[len(old):]
    return key


_NON_ALNUM = re.compile(r"[^a-z0-9]")


@lru_cache(maxsize=4096)
def norm(text):
    return _NON_ALNUM.sub("", str(text).lower())


_PREVIEW = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))


def fmt(value, limit=80):
    """How a value is shown in the tables."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        # Encode lazily and stop once the cell is full, instead of turning a list of thousands
        # of waypoints into JSON in full for every row on every refresh.
        parts, size = [], 0
        for chunk in _PREVIEW.iterencode(value):
            parts.append(chunk)
            size += len(chunk)
            if size > limit:
                break
        text = "".join(parts)
    else:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def same(a, b):
    """Equality that doesn't let True == 1 slip through."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def is_conflict(s):
    return s.rec is not None and not same(s.value, s.rec)


def status_text(s):
    return f"conflict; expect {fmt(s.rec)}" if is_conflict(s) else "OK"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


_SPLIT = re.compile(r"[_\-\s]+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_ACRONYMS = frozenset("ui hud esp gui api fps hp xp id npc uuid url rgb fov ah bz tps pvp bin".split())
_MINOR = frozenset("and or of the in on to for a an".split())
_GENERIC = frozenset("enabled enable toggle active state on value".split())
_CONTAINERS = frozenset("position pos offset color colour size scale".split())


@lru_cache(maxsize=None)
def words(segment):
    """'enableTeleportOverlays' / 'etherwarp-overlay' -> 'Enable Teleport Overlays' / 'Etherwarp Overlay'."""
    out = []
    for w in filter(None, _SPLIT.split(segment)):
        low = w.lower()
        if low in _ACRONYMS:
            out.append(low.upper())
        elif out and low in _MINOR:
            out.append(low)
        elif w.isupper() and len(w) > 1:
            out.append(w)
        else:
            out.append(w[0].upper() + w[1:])
    return " ".join(out) or segment


def make_label(mod, key, segments):
    """Menu-style name for a setting, built from its last config keys."""
    if (mod, key) in LABELS:
        return LABELS[(mod, key)]
    leaf = str(segments[-1])
    parent = str(segments[-2]) if len(segments) > 1 else ""
    if parent and leaf.lower() in _GENERIC:
        return words(parent)
    if parent and norm(parent) != norm(leaf):
        if len(segments) > 2 and parent.lower() in _CONTAINERS:       # "Feature › Position › X"
            return f"{words(str(segments[-3]))} › {words(parent)} › {words(leaf)}"
        return f"{words(parent)} › {words(leaf)}"
    return words(leaf)


_STRING = r'"[^"\\]*(?:\\.[^"\\]*)*"'
_TOKENS = re.compile(_STRING + r"|//[^\n]*|/\*.*?\*/", re.S)
_COMMAS = re.compile(_STRING + r"|,(\s*[}\]])", re.S)
_NOT_NEWLINE = re.compile(r"[^\n]")


def parse_jsonc(text):
    """json.loads that also accepts // and /* */ comments and trailing commas.

    Strings are matched first, so a URL like "https://x" is never mistaken for a comment.
    Returns (data, had_comments).
    """
    try:                                         # fast path: most configs are plain JSON, and the
        return json.loads(text), False           # C parser is far quicker than the regex passes
    except ValueError:
        pass
    found = False

    def blank(m):
        nonlocal found
        s = m.group(0)
        if s[0] == '"':
            return s
        found = True
        return _NOT_NEWLINE.sub(" ", s)          # keep line numbers intact for error messages

    text = _TOKENS.sub(blank, text)
    text = _COMMAS.sub(lambda m: m.group(1) if m.group(1) is not None else m.group(0), text)
    return json.loads(text), found


def leaves(root):
    """Yield (real path, display path, value) for every editable value in a JSON tree.

    Lists of {"name": ...} objects are addressed by name for display but by index for writing,
    so edits always land back in the right place.

    Walks with an explicit stack (same order as a recursive walk), so deeply nested files
    can't raise RecursionError and there's no per-level generator overhead.
    """
    stack = [(root, (), ())]
    pop, extend = stack.pop, stack.extend
    while stack:
        node, path, shown = pop()
        if isinstance(node, dict):
            extend([(v, path + (k,), shown + (k,)) for k, v in reversed(list(node.items()))])
        elif isinstance(node, list):
            if node and all(isinstance(x, dict) and "name" in x for x in node):
                kids = []
                for i, item in enumerate(node):
                    name = str(item["name"])
                    kids += [(v, path + (i, k), shown + (name, k)) for k, v in item.items() if k != "name"]
                extend(reversed(kids))
            else:
                yield path, shown, node
        elif node is not None:
            yield path, shown, node


def parse_value(text, old):
    """Turn what the user typed into a value of the same type as `old`."""
    t = text.strip()
    if isinstance(old, bool):
        if t.lower() in ("true", "1", "yes", "on"):
            return True
        if t.lower() in ("false", "0", "no", "off"):
            return False
        raise ValueError("Enter true or false.")
    if isinstance(old, int):
        try:
            return int(t)
        except ValueError:
            raise ValueError("Enter a whole number.") from None
    if isinstance(old, float):
        try:
            number = float(t)
        except ValueError:
            raise ValueError("Enter a number.") from None
        if not math.isfinite(number):
            raise ValueError("Enter a finite number.")
        return number
    if isinstance(old, (list, dict)):
        try:
            value = json.loads(t)
        except ValueError as e:
            raise ValueError(f"Not valid JSON: {e}") from None
        if not isinstance(value, type(old)):
            raise ValueError("Enter a JSON " + ("list." if isinstance(old, list) else "object."))
        return value
    return text


def atomic_write(path, text):
    """Write through a temp file and rename, so a crash can't leave a half-written config."""
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        try:
            shutil.copymode(path, tmp)
        except OSError:
            pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.chmod(tmp, 0o600)        # copymode may have made it read-only, and Windows
        except OSError:                 # won't delete a read-only file
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def find_files(folder, spec):
    """Config files for one mod. Unreadable folders count as "not found" instead of raising."""
    d = spec.get("dir")
    if d:
        try:
            found = sorted(p for p in (folder / d).iterdir()
                           if p.suffix.lower() in (".json", ".jsonc") and p.is_file())
        except OSError:
            found = []
        if found:
            return found
    for rel in spec.get("files", ()):
        p = folder / rel
        try:
            if p.is_file():
                return [p]
        except OSError:
            continue
    return []


_INDENT = re.compile(r"^[{\[][ \t]*(?:/\*.*?\*/)?[ \t]*\r?\n([ \t]+)\S", re.S)


def detect_indent(text):
    """The file's own layout, so saving doesn't reformat the whole file: its indent ("\\t",
    2, 4 ...), or None for a file written on a single line."""
    body = text.strip()
    if "\n" not in body:
        return None
    m = _INDENT.match(body)
    if not m:
        return 2
    ws = m.group(1)
    return "\t" if "\t" in ws else len(ws)


def exe_dir():
    """Folder holding the packaged .exe (None when running as a script)."""
    return Path(sys.executable).resolve().parent if FROZEN else None


def detect_config_dir(hints=()):
    home = Path.home()
    cands = [Path(h) for h in hints if isinstance(h, str) and h]
    bases = []
    try:
        bases.append(Path.cwd())
    except OSError:                                  # the working folder was deleted
        pass
    if FROZEN:                                       # look around wherever the .exe was put
        bases.append(exe_dir())
        cands.append(exe_dir().parent / "config")    # e.g. the .exe sits in .minecraft/mods
    for b in dict.fromkeys(bases):
        cands += [b, b / "config", b / "minecraft" / "config", b / ".minecraft" / "config"]
    if os.environ.get("APPDATA"):
        cands.append(Path(os.environ["APPDATA"]) / ".minecraft" / "config")
    cands += [home / ".minecraft" / "config", home / "Library" / "Application Support" / "minecraft" / "config"]
    for c in cands:
        try:
            if c.is_dir() and any(find_files(c, spec) for spec in MODS.values()):
                return str(c)
        except OSError:
            continue
    return ""


# ── installed jars & update check ──

_JAR_META = {}        # jar path -> ((size, mtime_ns), (mod id, version) or None)
_SHA1 = {}            # jar path -> ((size, mtime_ns), sha1)
_CACHE_LOCK = threading.Lock()


def _stamp(p):
    st = p.stat()
    return st.st_size, st.st_mtime_ns


def _jar_meta(jar, stamp):
    """(mod id, version) from a jar's fabric.mod.json, cached until the jar changes."""
    hit = _JAR_META.get(jar)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        with zipfile.ZipFile(jar) as z:
            meta = json.loads(z.read("fabric.mod.json").decode("utf-8-sig"))
        info = ((str(meta.get("id", "")), str(meta.get("version") or "?"))
                if isinstance(meta, dict) else None)
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, RecursionError):
        info = None
    _JAR_META[jar] = (stamp, info)
    return info


def installed_jars(mods_dir):
    """{mod name: (version, jar path)} found by the mod id inside each jar's fabric.mod.json.

    Only jars that changed since the last scan are opened again, so Reload stays instant
    even with a few hundred mods installed.
    """
    by_id = {spec["id"]: name for name, spec in MODS.items() if spec.get("id")}
    jars = []
    try:
        for p in Path(mods_dir).iterdir():
            if p.suffix.lower() == ".jar":
                try:
                    jars.append((p, _stamp(p)))
                except OSError:
                    continue
    except OSError:
        return {}
    jars.sort(key=lambda js: js[1][1], reverse=True)       # newest first if a mod is there twice
    found = {}
    for jar, stamp in jars:
        info = _jar_meta(jar, stamp)
        name = by_id.get(info[0]) if info else None
        if name and name not in found:
            found[name] = (info[1], jar)
    return found


def sha1_file(path):
    path = Path(path)
    stamp = _stamp(path)
    with _CACHE_LOCK:
        hit = _SHA1.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    with _CACHE_LOCK:
        _SHA1[path] = (stamp, digest)
    return digest


def version_core(v):
    """Drop the parts that only say which Minecraft version a build is for.

    'v6.11.0+26.1.2' -> '6.11.0', '44.3.0+mc26.1' -> '44.3.0', '0.7.2-beta.3-26.1.X' -> '0.7.2-beta.3'
    """
    v = str(v).strip().lower()
    v = v[1:] if v.startswith("v") else v
    v = v.split("+", 1)[0]
    return re.sub(r"[-_](?:mc-?)?\d{2}\.\d+(?:\.(?:\d+|x))*$", "", v)


def version_key(v):
    """Sortable form of a version: release beats beta of the same number. None if unparseable."""
    m = re.match(r"(\d+(?:\.\d+)*)(.*)$", version_core(v))
    if not m:
        return None
    main = tuple(int(x) for x in m.group(1).split("."))
    main += (0,) * (4 - len(main))
    rest = m.group(2)
    pre = (1,) if not rest else (0,) + tuple(int(x) for x in re.findall(r"\d+", rest))
    return main, pre


API = "https://api.modrinth.com/v2"
UA = f"skyblock-config-manager/{__version__}"


def http_json(url, data=None, timeout=15):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {"User-Agent": UA}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _compare(installed, latest):
    a, b = version_key(installed), version_key(latest)
    if a is None or b is None:
        return (f"Modrinth: {latest}", "info") if version_core(installed) != version_core(latest) \
            else ("up to date", "ok")
    return (f"↑ {latest}", "new") if b > a else ("up to date", "ok")


def modrinth_status(jars):
    """{mod name: (text, state)} for installed jars, against Fabric GAME_VERSION builds only.

    First asks Modrinth which project each exact jar file belongs to (by SHA-1), which avoids
    every naming difference. Jars Modrinth doesn't know fall back to the project slug.
    state: "ok" (up to date), "new" (update available), "info", "missing", "failed".
    """
    names = list(jars)
    if not names:
        return {}
    with ThreadPoolExecutor(max_workers=min(8, len(names))) as pool:
        hashes = dict(zip(names, pool.map(lambda n: sha1_file(jars[n][1]), names)))
    latest = http_json(f"{API}/version_files/update", {
        "hashes": sorted(set(hashes.values())), "algorithm": "sha1",
        "loaders": [LOADER], "game_versions": [GAME_VERSION]})
    if not isinstance(latest, dict):
        latest = {}
    out, fallback = {}, []
    for name in names:
        installed, h = jars[name][0], hashes[name]
        v = latest.get(h)
        if isinstance(v, dict) and v.get("version_number"):
            files = [(f.get("hashes") or {}).get("sha1") for f in v.get("files") or ()
                     if isinstance(f, dict)]
            out[name] = ("up to date", "ok") if h in files else _compare(installed, v["version_number"])
        elif MODS.get(name, {}).get("slug"):
            fallback.append(name)
        else:
            out[name] = ("not on Modrinth", "missing")

    q = urllib.parse.urlencode({"loaders": json.dumps([LOADER]),
                                "game_versions": json.dumps([GAME_VERSION])})

    def by_slug(name):
        slug = urllib.parse.quote(MODS[name]["slug"], safe="")
        try:
            versions = http_json(f"{API}/project/{slug}/version?{q}")
            if not isinstance(versions, list) or not versions:
                return f"no {GAME_VERSION} build", "missing"
            return _compare(jars[name][0], versions[0]["version_number"])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "not on Modrinth", "missing"
            return f"check failed (HTTP {e.code})", "failed"
        except (OSError, ValueError, KeyError, TypeError):    # this mod only; keep the others
            return "check failed", "failed"

    if fallback:                                   # independent requests: run them side by side
        with ThreadPoolExecutor(max_workers=min(6, len(fallback))) as pool:
            out.update(zip(fallback, pool.map(by_slug, fallback)))
    return out


# ── preferences ──

def prefs_files():
    """Where settings may be kept, preferred first.

    The .exe is portable: it keeps its settings in a file beside itself, and only falls back
    to the home folder when it can't write there (e.g. it was put in Program Files).
    """
    if FROZEN:
        return [exe_dir() / PORTABLE_PREFS, HOME_PREFS]
    return [HOME_PREFS]


def load_prefs():
    """The newest readable settings file, so an older copy never shadows the one last saved
    (this also carries settings over from the script version to the .exe)."""
    found = []
    for path in prefs_files():
        try:
            found.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for _mtime, path in sorted(found, key=lambda mp: mp[0], reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        pr = data.get("priority")
        if isinstance(pr, dict):                     # areas were renamed in this version
            data["priority"] = {OLD_AREA_NAMES.get(k, k): v for k, v in pr.items()
                                if isinstance(k, str) and isinstance(v, str)}
        ov = data.get("overrides")
        if isinstance(ov, dict):                     # keys are "Area/Feature"
            data["overrides"] = {renamed_area_key(k): v for k, v in ov.items()
                                 if isinstance(k, str) and isinstance(v, str)}
        return data
    return {}


def save_prefs(prefs):
    text = json.dumps(prefs, indent=2)
    for path in prefs_files():
        try:
            atomic_write(path, text)
            return
        except OSError:
            continue


def app_icon():
    """The window icon (.ico): bundled inside the .exe, or packaging/icon.ico next to the script."""
    base = (Path(getattr(sys, "_MEIPASS", exe_dir())) if FROZEN
            else Path(__file__).resolve().parent / "packaging")
    p = base / "icon.ico"
    return p if p.is_file() else None


# ═════════════════════════════════════════ Model ═════════════════════════════════════════════

class ConfigFile:
    __slots__ = ("path", "raw", "comments", "backup", "warned", "indent", "stamp")

    def __init__(self, path, raw, comments, indent=2, stamp=None):
        self.path, self.raw, self.comments = path, raw, comments
        self.backup, self.warned = None, False
        self.indent, self.stamp = indent, stamp          # stamp: (size, mtime_ns) when loaded


class Setting:
    __slots__ = ("uid", "mod", "cf", "path", "key", "label", "value", "orig", "hay",
                 "shared", "domain", "feature", "rec", "order")

    def __init__(self, uid, mod, cf, path, key, label, value):
        self.uid, self.mod, self.cf, self.path, self.key, self.label = uid, mod, cf, path, key, label
        self.value = self.orig = value
        self.hay = f"{mod} {label} {key}".lower()      # built once, so searching is just `in`
        self.shared, self.domain, self.feature, self.rec, self.order = False, "", None, None, ()


class ModInfo:
    __slots__ = ("name", "files", "errors", "settings", "shared", "installed", "jar", "latest")

    def __init__(self, name):
        self.name, self.files, self.errors, self.settings = name, [], [], []
        self.shared, self.installed, self.jar, self.latest = 0, None, None, None

    @property
    def loaded(self):
        return bool(self.files)


class Feature:
    """One row of FEATURES, resolved against the loaded configs."""
    __slots__ = ("index", "area", "name", "key", "spec", "switches", "winner")

    def __init__(self, index, area, name, spec):
        self.index, self.area, self.name, self.spec = index, area, name, spec
        self.key = f"{area}/{name}"
        self.switches = {}              # {mod: [Setting]} for every mod that competes here
        self.winner = None              # mod whose switches stay on, or None for "Off"

    @property
    def contenders(self):
        return list(self.switches)

    @property
    def live(self):
        """Two or more of your mods offer it, and at least one has a switch to flip."""
        return len(self.switches) > 1 and any(self.switches.values())


class Workspace:
    """Everything except the window: loading, recommendations, editing, saving."""

    def __init__(self, priority=None, overrides=None):
        self.folder = None
        self.mods, self.settings, self.index = {}, [], {}
        self.changed = set()                 # uids whose value differs from what is on disk
        self.priority = ({str(k): str(v) for k, v in priority.items()}
                         if isinstance(priority, dict) else {})
        self.overrides = ({str(k): str(v) for k, v in overrides.items()}
                          if isinstance(overrides, dict) else {})
        self.features = [Feature(i, a, n, spec) for i, (a, n, spec) in enumerate(FEATURES)]
        self.choices, self.owner = {}, {}
        self.shared, self.unique, self._ruled = [], [], []

    # ── loading ──
    def load(self, folder):
        folder = Path(folder).expanduser()
        if not folder.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder}")
        # Build everything into locals first, so a failure can't leave a half-loaded workspace.
        mods, settings, index = {}, [], {}
        for name, spec in MODS.items():
            info = mods[name] = ModInfo(name)
            for path in find_files(folder, spec):
                try:
                    stamp = _stamp(path)
                    if stamp[0] > MAX_FILE_BYTES:
                        raise ValueError("file is larger than 25 MB")
                    text = path.read_text(encoding="utf-8-sig")
                    raw, comments = parse_jsonc(text)
                except (OSError, ValueError, RecursionError) as e:
                    info.errors.append(f"{path.name} ({e})")
                    continue
                if not isinstance(raw, (dict, list)):
                    info.errors.append(f"{path.name} (not a JSON object)")
                    continue
                cf = ConfigFile(path, raw, comments, detect_indent(text), stamp)
                info.files.append(cf)
                prefix = (path.stem,) if spec.get("dir") else ()
                for real, shown, value in leaves(raw):
                    if not real:
                        continue
                    shown = prefix + shown
                    key = ".".join(map(str, shown))
                    s = Setting(len(settings), name, cf, real, key,
                                make_label(name, key, shown), value)
                    settings.append(s)
                    info.settings.append(s)
                    index.setdefault((name, key), s)       # duplicate names: first one wins
        self.folder, self.mods, self.settings, self.index = folder, mods, settings, index
        self.changed = set()
        self._ruled = []
        self._resolve_features()
        self.recompute()

    def _match(self, mod, key, by_leaf):
        if key.startswith("*"):
            tail = key.lstrip("*.")
            dotted = "." + tail
            leaf = tail.rsplit(".", 1)[-1]
            return [s for s in by_leaf.get(leaf, ()) if s.key == tail or s.key.endswith(dotted)]
        s = self.index.get((mod, key))
        return [s] if s else []

    def _resolve_features(self):
        """Find each feature's switches in the loaded configs (done once per load)."""
        leaf_index = {}                      # mod -> {last key segment: [Setting]}, built lazily

        def by_leaf(mod):
            if mod not in leaf_index:
                d = leaf_index[mod] = {}
                for s in self.mods[mod].settings:
                    d.setdefault(s.key.rsplit(".", 1)[-1], []).append(s)
            return leaf_index[mod]

        for f in self.features:
            f.switches = {}
            for mod, spec in f.spec.items():
                if mod not in self.mods or not self.mods[mod].loaded:
                    continue
                if spec is None:
                    f.switches[mod] = []
                    continue
                found, seen = [], set()
                for key in ([spec] if isinstance(spec, str) else spec):
                    leaf = by_leaf(mod) if key.startswith("*") else None
                    for s in self._match(mod, key, leaf):
                        if isinstance(s.value, bool) and s.uid not in seen:
                            seen.add(s.uid)
                            found.append(s)
                if found:
                    f.switches[mod] = found

    # ── recommendations ──
    def live_features(self, area=None):
        return [f for f in self.features if f.live and (area is None or f.area == area)]

    def recompute(self):
        """Work out which setting should be what, from the loaded mods and the priorities."""
        for s in self._ruled:
            s.rec, s.shared, s.domain, s.feature, s.order = None, False, "", None, ()
        for m in self.mods.values():
            m.shared = 0

        live = self.live_features()
        self.choices, self.owner = {}, {}
        for f in live:
            pool = self.choices.setdefault(f.area, [])
            pool.extend(m for m in f.contenders if m not in pool)
        self.choices = {a: self.choices[a] for a in AREAS if a in self.choices}
        for area, pool in self.choices.items():
            want = self.priority.get(area)
            self.owner[area] = want if want in pool else pool[0]

        ruled, seen = [], set()
        for f in self.features:
            f.winner = None
        for f in live:
            present, owner, ov = f.contenders, self.owner[f.area], self.overrides.get(f.key)
            if ov == OFF:
                f.winner = None
            elif ov in present:
                f.winner = ov
            else:
                f.winner = owner if owner in present else present[0]
            area_i = AREAS.index(f.area) if f.area in AREAS else len(AREAS)
            for rank, mod in enumerate(sorted(present, key=lambda m: m != f.winner)):
                for j, s in enumerate(f.switches[mod]):
                    if s.uid in seen:                # a key listed under two features: first wins
                        continue
                    seen.add(s.uid)
                    s.rec, s.shared, s.domain, s.feature = (mod == f.winner), True, f.area, f
                    s.order = (area_i, f.index, rank, j)
                    self.mods[mod].shared += 1
                    ruled.append(s)
        for mod, key, want in PREFERRED:
            s = self.index.get((mod, key))
            if s is not None and not s.shared and isinstance(s.value, bool) == isinstance(want, bool):
                s.rec = want
                ruled.append(s)
        self._ruled = ruled
        self.shared = sorted((s for s in ruled if s.shared), key=lambda s: s.order)
        self.unique = [s for s in self.settings if not s.shared]

    def set_priority(self, area, mod):
        self.priority[area] = mod
        self.recompute()

    def set_override(self, feature_key, mod):
        """mod: a mod name, OFF, or None to follow the area's choice."""
        if mod is None:
            self.overrides.pop(feature_key, None)
        else:
            self.overrides[feature_key] = mod
        self.recompute()

    def conflicts(self):
        """(per mod, per area, per feature key) conflict counts."""
        by_mod, by_area, by_feature = {}, {}, {}
        for s in self._ruled:
            if is_conflict(s):
                by_mod[s.mod] = by_mod.get(s.mod, 0) + 1
                if s.shared:
                    by_area[s.domain] = by_area.get(s.domain, 0) + 1
                    by_feature[s.feature.key] = by_feature.get(s.feature.key, 0) + 1
        return by_mod, by_area, by_feature

    # ── editing ──
    def set_value(self, s, value):
        node = s.cf.raw
        for step in s.path[:-1]:
            node = node[step]
        node[s.path[-1]] = value
        s.value = value
        if same(value, s.orig):
            self.changed.discard(s.uid)
        else:
            self.changed.add(s.uid)

    def resolve(self, area=None, feature_key=None):
        """Apply recommended values: everywhere, for one area, or for one feature."""
        n = 0
        for s in self._ruled:
            if not is_conflict(s):
                continue
            if area is not None and not (s.shared and s.domain == area):
                continue
            if feature_key is not None and not (s.shared and s.feature.key == feature_key):
                continue
            self.set_value(s, s.rec)
            n += 1
        return n

    # ── saving ──
    def dirty_files(self):
        return list(dict.fromkeys(self.settings[uid].cf for uid in sorted(self.changed)))

    def save(self):
        """Write every modified file, backing each up once. Returns (saved names, errors).

        A file that something else (usually the game) rewrote since it was loaded is skipped,
        so its newer settings aren't silently overwritten with stale ones.
        """
        stamp = time.strftime("%Y%m%d_%H%M%S")
        saved, errors = [], []
        by_file = {}
        for uid in self.changed:
            by_file.setdefault(self.settings[uid].cf, []).append(uid)
        for cf in self.dirty_files():
            try:
                if cf.stamp is not None and _stamp(cf.path) != cf.stamp:
                    raise ValueError("it was changed on disk after loading (is the game running?). "
                                     "Reload, then make the change again")
                if cf.backup is None:
                    bak = cf.path.with_name(f"{cf.path.name}.bak_{stamp}")
                    # Never overwrite an earlier backup (saving again within the same second,
                    # after a Reload, used to replace the original file's backup).
                    n = 1
                    while bak.exists():
                        bak = cf.path.with_name(f"{cf.path.name}.bak_{stamp}_{n}")
                        n += 1
                    # copyfile + copystat = copy2, minus its use of the CopyFile2 API (Python
                    # 3.12+ on Windows), which some Wine/Proton/CrossOver versions lack.
                    shutil.copyfile(cf.path, bak)
                    shutil.copystat(cf.path, bak)
                    cf.backup = bak
                if cf.indent is None:                 # written on one line: keep it that way
                    text = json.dumps(cf.raw, ensure_ascii=False, separators=(",", ":"))
                else:
                    text = json.dumps(cf.raw, indent=cf.indent, ensure_ascii=False)
                atomic_write(cf.path, text + "\n")
                try:
                    cf.stamp = _stamp(cf.path)
                except OSError:
                    cf.stamp = None
            except (OSError, ValueError) as e:
                errors.append(f"{cf.path.name}: {e}")
                continue
            for uid in by_file[cf]:
                self.settings[uid].orig = self.settings[uid].value
                self.changed.discard(uid)
            saved.append(cf.path.name)
        return saved, errors


# ═══════════════════════════════════════════ GUI ═════════════════════════════════════════════

BG, PANEL, RAISED, LINE = "#14161b", "#1b1e25", "#242832", "#2d323d"
FG, MUTED, DIM = "#e4e7ec", "#8c94a3", "#5b6270"
ACCENT, ACCENT_DARK, ON_ACCENT = "#4cc4a2", "#3aa688", "#0c1714"
SELECT, HOVER = "#1f3a33", "#2b303b"
BAD, BAD_BG, GOOD, NEW = "#ff8f80", "#2e1d1f", "#7fd3ab", "#f2c46d"

FOLLOW = "Area choice"            # combobox prefix for "follow the area's prioritized mod"
OFF_LABEL = "Off in every mod"


def dark_title_bar(win):
    """Ask Windows 10/11 for a dark title bar; silently does nothing elsewhere."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        on = ctypes.c_int(1)
        for attr in (20, 19):                      # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on),
                                                          ctypes.sizeof(on)) == 0:
                break
    except Exception:
        pass


class EditDialog(tk.Toplevel):
    """Small themed prompt for typing a new value. `result` holds the parsed value or None."""

    def __init__(self, app, s):
        super().__init__(app)
        px = app.px
        self.s, self.result = s, None
        self.withdraw()
        self.title("Edit setting")
        self.configure(background=BG)
        self.resizable(False, False)
        self.transient(app)
        body = ttk.Frame(self, padding=px(18))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{s.mod} › {s.label}", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text=f"{s.key}  ·  {type(s.value).__name__}", style="Muted.TLabel"
                  ).pack(anchor="w", pady=(px(2), px(12)))
        current = (json.dumps(s.value, ensure_ascii=False)
                   if isinstance(s.value, (list, dict)) else str(s.value))
        self.var = tk.StringVar(value=current)
        entry = ttk.Entry(body, textvariable=self.var, width=46)
        entry.pack(fill="x")
        self.error = ttk.Label(body, text="", style="Bad.TLabel")
        self.error.pack(anchor="w", pady=(px(6), 0))
        row = ttk.Frame(body)
        row.pack(fill="x", pady=(px(10), 0))
        ttk.Button(row, text="Save", style="Accent.TButton", command=self.ok).pack(side="right")
        ttk.Button(row, text="Cancel", command=self.destroy).pack(side="right", padx=(0, px(8)))
        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_reqwidth()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        dark_title_bar(self)
        entry.focus_set()
        entry.select_range(0, "end")
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def ok(self):
        try:
            self.result = parse_value(self.var.get(), self.s.value)
        except ValueError as e:
            self.error.configure(text=str(e))
            return
        self.destroy()


class ScrollFrame(ttk.Frame):
    """A frame whose content scrolls vertically; the scrollbar only shows when needed."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background=BG, highlightthickness=0, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", lambda _e: self._sync())
        self.canvas.bind("<Configure>", lambda e: (self.canvas.itemconfigure(self._win, width=e.width),
                                                   self._sync()))
        # The wheel handler is registered with Tcl once and then bound by name. Binding Python
        # functions on every <Enter> created three Tcl commands each time, never freed.
        wheel = self.register(self._on_delta)
        self._wheel_scripts = {"<MouseWheel>": f"{wheel} %D", "<Button-4>": f"{wheel} 120",
                               "<Button-5>": f"{wheel} -120"}
        for w in (self, self.canvas, self.inner):
            w.bind("<Enter>", lambda _e: self._wheel(True), add="+")
            w.bind("<Leave>", lambda _e: self._wheel(False), add="+")

    def _contains_pointer(self):
        """True if the mouse is over this frame or any widget inside it."""
        try:
            w = self.winfo_containing(*self.winfo_pointerxy())
        except (tk.TclError, KeyError):            # KeyError: pointer over a non-Tk window/popup
            return False
        me = str(self)
        return w is not None and (str(w) == me or str(w).startswith(me + "."))

    def passthrough(self, widget):
        """Make the wheel scroll this frame instead of changing a combobox's value."""
        for seq, script in self._wheel_scripts.items():
            widget.bind(seq, script + "\nbreak")

    def _sync(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        need = self.inner.winfo_reqheight() > self.canvas.winfo_height() > 1
        if need and not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        elif not need and self.bar.winfo_ismapped():
            self.bar.pack_forget()
            self.canvas.yview_moveto(0)

    def _wheel(self, on):
        # <Leave> also fires when the pointer moves onto a child (a label, a combobox), which
        # used to switch scrolling off while over the rows; only unbind once it really left.
        if on:
            for seq, script in self._wheel_scripts.items():
                self.bind_all(seq, script)
        elif not self._contains_pointer():
            for seq in self._wheel_scripts:
                self.unbind_all(seq)

    def _on_delta(self, delta):
        try:
            d = float(delta)
        except ValueError:
            return
        if d:
            self._scroll(-1 if d > 0 else 1)

    def _scroll(self, step):
        if self.bar.winfo_ismapped():
            self.canvas.yview_scroll(step * 3, "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


class SettingsView(ttk.Frame):
    """A searchable table of settings, used for both the Shared and Unique tabs."""

    COLUMNS = (("mod", "Mod", 110, False), ("setting", "Setting", 340, True),
               ("current", "Current", 150, False), ("rec", "Recommended", 130, False),
               ("status", "Status", 190, False))
    LIMIT = 2500                              # rows drawn at once; keeps huge configs snappy

    def __init__(self, app, source, group_label, group_of):
        px = app.px
        super().__init__(app.notebook, padding=(0, px(14), 0, 0))
        self.app, self.source, self.group_of = app, source, group_of
        self._shown, self._timer, self._painted = [], None, {}

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, px(10)))
        ttk.Label(bar, text="Search", style="Muted.TLabel").pack(side="left")
        self.query = tk.StringVar()
        self.query.trace_add("write", lambda *_: self._debounce())
        ttk.Entry(bar, textvariable=self.query, width=26).pack(side="left", padx=(px(8), px(18)))
        ttk.Label(bar, text=group_label, style="Muted.TLabel").pack(side="left")
        self.group = tk.StringVar(value=ALL)
        self.group_box = ttk.Combobox(bar, textvariable=self.group, values=[ALL],
                                      state="readonly", width=16)
        self.group_box.pack(side="left", padx=(px(8), px(18)))
        self.group_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.only_bad = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Conflicts only", variable=self.only_bad,
                        command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Edit…", command=self.edit).pack(side="right")
        self.btn_rec = ttk.Button(bar, text="Use recommended", command=self.use_recommended,
                                  state="disabled")
        self.btn_rec.pack(side="right", padx=(0, px(8)))

        box = ttk.Frame(self, style="Card.TFrame", padding=1)
        box.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(box, columns=[c[0] for c in self.COLUMNS], show="headings",
                                 selectmode="browse")
        bar_y = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar_y.pack(side="right", fill="y")
        for key, title, width, stretch in self.COLUMNS:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=px(width), minwidth=px(70), stretch=stretch, anchor="w")
        self.tree.tag_configure("bad", foreground=BAD, background=BAD_BG)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Return>", lambda _e: self.edit())
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        foot = ttk.Frame(self)
        foot.pack(fill="x", pady=(px(8), 0))
        self.count = ttk.Label(foot, style="Muted.TLabel")
        self.count.pack(side="left")
        self.where = ttk.Label(foot, style="Muted.TLabel")
        self.where.pack(side="right")

    # ── content ──
    def reset(self):
        """Forget everything shown (used when a different load replaces the settings)."""
        self.tree.delete(*self.tree.get_children())
        self._shown, self._painted = [], {}

    def set_groups(self, values):
        self.group_box.configure(values=[ALL, *values])
        if self.group.get() not in (ALL, *values):
            self.group.set(ALL)

    @staticmethod
    def _values(s):
        return (s.mod, s.label, fmt(s.value), "—" if s.rec is None else fmt(s.rec), status_text(s))

    @staticmethod
    def _tags(s):
        return ("bad",) if is_conflict(s) else ()

    def _debounce(self):
        if self._timer:
            self.after_cancel(self._timer)
        self._timer = self.after(180, self.refresh)

    def refresh(self):
        if self._timer:                               # a direct refresh supersedes a pending one
            self.after_cancel(self._timer)
        self._timer = None
        terms = self.query.get().lower().split()
        group, only_bad = self.group.get(), self.only_bad.get()
        rows = self.source()                          # narrow with the cheapest test first
        if group != ALL:
            group_of = self.group_of
            rows = [s for s in rows if group_of(s) == group]
        if only_bad:
            rows = [s for s in rows if is_conflict(s)]
        for t in terms:
            rows = [s for s in rows if t in s.hay]
        total, rows = len(rows), rows[: self.LIMIT]
        if rows == self._shown:                       # same rows: only touch the ones that changed
            for s in rows:
                self._paint_row(s)
        else:
            tree, keep = self.tree, self.tree.selection()
            tree.delete(*tree.get_children())
            self._painted = {}
            for s in rows:
                values, tags = self._values(s), self._tags(s)
                tree.insert("", "end", iid=str(s.uid), values=values, tags=tags)
                self._painted[s.uid] = (values, tags)
            self._shown = rows
            if keep and tree.exists(keep[0]):
                tree.selection_set(keep[0])
                tree.see(keep[0])
        note = plural(total, "setting")
        if total > self.LIMIT:
            note += f" · showing the first {self.LIMIT:,}, search to narrow"
        self.count.configure(text=note)
        self._on_select()

    def _paint_row(self, s):
        now = (self._values(s), self._tags(s))
        if self._painted.get(s.uid) != now:
            self.tree.item(str(s.uid), values=now[0], tags=now[1])
            self._painted[s.uid] = now

    def paint(self, s):
        """Update one row after an edit (no-op if the row isn't currently in the table)."""
        if s.uid in self._painted:
            self._paint_row(s)
            self._on_select()

    # ── selection / actions ──
    def selected(self):
        sel = self.tree.selection()
        return self.app.ws.settings[int(sel[0])] if sel else None

    def _on_select(self, _e=None):
        s = self.selected()
        where = ""
        if s:
            where = f"{s.mod} › {s.key}"
            if s.shared:
                where = f"{s.domain} › {s.feature.name}   ·   {where}"
        self.where.configure(text=where)
        self.btn_rec.state(["!disabled"] if s and is_conflict(s) else ["disabled"])

    def _on_double(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell":
            self.edit()

    def edit(self):
        s = self.selected()
        if s:
            self.app.edit_setting(s)
        else:
            self.app.say("Select a setting first.")

    def use_recommended(self):
        s = self.selected()
        if s and is_conflict(s):
            self.app.apply(s, s.rec)


class PrioritiesView(ttk.Frame):
    """Area list on the left (one tab per area), the chosen area's features on the right."""

    def __init__(self, app):
        px = app.px
        super().__init__(app.notebook, padding=(0, px(14), 0, 0))
        self.app = app
        self.area = AREAS[0]
        self.rows = {}               # feature key -> widgets of that row

        side = ttk.Frame(self, style="Card.TFrame", padding=1)
        side.pack(side="left", fill="y")
        self.side = ttk.Treeview(side, columns=("n",), show="tree", selectmode="browse",
                                 style="Side.Treeview", height=len(AREAS))
        self.side.column("#0", width=px(132), stretch=False)
        self.side.column("n", width=px(46), anchor="e", stretch=False)
        self.side.tag_configure("dim", foreground=DIM)
        self.side.tag_configure("bad", foreground=BAD)
        for a in AREAS:
            self.side.insert("", "end", iid=a, text="  " + a, values=("",))
        self.side.pack(fill="y", expand=True)
        self.side.bind("<<TreeviewSelect>>", self._on_area)

        self.body = ScrollFrame(self)
        self.body.pack(side="left", fill="both", expand=True, padx=(px(22), 0))

    # ── building ──
    def rebuild(self):
        """Redraw the area panel (after a load or when switching areas)."""
        px, ws, app = self.app.px, self.app.ws, self.app
        if self.side.selection() != (self.area,):
            self.side.selection_set(self.area)
        self.body.clear()
        self.rows = {}
        inner = self.body.inner
        inner.columnconfigure(2, weight=1)

        head = ttk.Frame(inner)
        head.grid(row=0, column=0, columnspan=4, sticky="ew")
        ttk.Label(head, text=self.area, style="Title.TLabel").pack(side="left")
        self.apply_btn = ttk.Button(head, text="Apply area", command=lambda: app.resolve(self.area))
        self.apply_btn.pack(side="right")
        self.area_status = ttk.Label(head, style="Muted.TLabel")
        self.area_status.pack(side="right", padx=px(12))

        feats = ws.live_features(self.area)
        if not feats:
            self.apply_btn.state(["disabled"])
            tracked = [f for f in ws.features if f.area == self.area]
            ttk.Label(inner, style="Muted.TLabel", wraplength=px(640), justify="left",
                      text=("No overlapping switches found in your configs for this area. " if ws.folder else
                            "Load your config folder to see overlaps. ")
                      + "These features are compared once two of their mods are installed:"
                      ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(px(14), px(8)))
            for r, f in enumerate(tracked, start=2):
                ttk.Label(inner, text=f.name, style="Dim.TLabel").grid(
                    row=r, column=0, sticky="w", pady=px(3), padx=(0, px(24)))
                ttk.Label(inner, text=", ".join(f.spec), style="Dim.TLabel").grid(
                    row=r, column=1, columnspan=3, sticky="w")
            self.update_view()
            return

        line = ttk.Frame(inner)
        line.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(px(14), px(4)))
        ttk.Label(line, text="Prioritized mod").pack(side="left")
        self.owner_var = tk.StringVar()
        box = ttk.Combobox(line, textvariable=self.owner_var, values=ws.choices[self.area],
                           state="readonly", width=16)
        box.pack(side="left", padx=px(10))
        box.bind("<<ComboboxSelected>>", lambda _e: app.set_priority(self.area, self.owner_var.get()))
        self.body.passthrough(box)
        ttk.Label(inner, style="Muted.TLabel", wraplength=px(640), justify="left",
                  text="Its version of every feature below stays on and the same feature in your "
                       "other mods is turned off. Pick a different mod for any single feature to "
                       "override it, or turn it off everywhere."
                  ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, px(14)))

        for c, text in enumerate(("Feature", "Use", "Turns off", "")):
            ttk.Label(inner, text=text, style="Head.TLabel").grid(
                row=3, column=c, sticky="w", padx=(0, px(18)), pady=(0, px(6)))
        for r, f in enumerate(feats, start=4):
            name = ttk.Label(inner, text=f.name)
            name.grid(row=r, column=0, sticky="w", padx=(0, px(18)), pady=px(4))
            var = tk.StringVar()
            combo = ttk.Combobox(inner, textvariable=var, state="readonly", width=22)
            combo.grid(row=r, column=1, sticky="w", padx=(0, px(18)))
            combo.bind("<<ComboboxSelected>>",
                       lambda _e, k=f.key, v=var: app.set_override(k, self._decode(v.get())))
            self.body.passthrough(combo)      # scrolling past it must not change the override
            off = ttk.Label(inner, style="Muted.TLabel")
            off.grid(row=r, column=2, sticky="w", padx=(0, px(18)))
            status = ttk.Label(inner, width=13)
            status.grid(row=r, column=3, sticky="e")
            self.rows[f.key] = (f, var, combo, off, status)
        self.update_view()

    @staticmethod
    def _decode(text):
        if text.startswith(FOLLOW):
            return None
        return OFF if text == OFF_LABEL else text

    # ── refreshing in place ──
    def update_view(self, counts=None):
        ws = self.app.ws
        _, by_area, by_feature = counts or ws.conflicts()
        for a in AREAS:
            live = a in ws.choices
            n = by_area.get(a, 0)
            self.side.item(a, values=(str(n) if n else ("✓" if live else ""),),
                           tags=("bad",) if n else (() if live else ("dim",)))
        n = by_area.get(self.area, 0)
        if self.area in ws.choices:
            self.area_status.configure(text=plural(n, "conflict") if n else "no conflicts")
            self.apply_btn.state(["!disabled"] if n else ["disabled"])
            self.owner_var.set(ws.owner[self.area])
        follow = f"{FOLLOW} ({ws.owner.get(self.area, '—')})"
        for key, (f, var, combo, off, status) in self.rows.items():
            combo.configure(values=[follow, *f.contenders, OFF_LABEL])
            ov = ws.overrides.get(key)
            var.set(OFF_LABEL if ov == OFF else ov if ov in f.contenders else follow)
            losers = [m for m in f.contenders if m != f.winner]
            off.configure(text=", ".join(losers) if losers else "—")
            k = by_feature.get(key, 0)
            status.configure(text=plural(k, "conflict") if k else "OK",
                             style="Bad.TLabel" if k else "Good.TLabel")

    def _on_area(self, _e=None):
        sel = self.side.selection()
        if sel and sel[0] != self.area:
            self.area = sel[0]
            self.rebuild()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._errors_shown, self._error_open = set(), False
        self.title("SkyBlock Config Manager")
        icon = app_icon() if sys.platform == "win32" else None
        if icon:
            try:
                self.iconbitmap(default=str(icon))          # also used by dialogs
            except tk.TclError:
                pass
        self.scale = max(1.0, self.winfo_fpixels("1i") / 96.0)
        self.geometry(f"{self.px(1160)}x{self.px(760)}")
        self.minsize(self.px(920), self.px(560))
        self.configure(background=BG)
        self.prefs = load_prefs()
        self.ws = Workspace(self.prefs.get("priority"), self.prefs.get("overrides"))
        self._queue = queue.Queue()
        self._style()
        self._build()
        dark_title_bar(self)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        for seq in ("<Control-s>", "<Control-S>"):         # also with Caps Lock on
            self.bind(seq, lambda _e: self.save())
        folder = detect_config_dir([self.prefs.get("config_dir", "")])
        if folder:
            self.after(50, lambda: self.load(folder))
        else:
            self.say("Choose your Minecraft config folder to begin.")

    def px(self, n):
        return int(round(n * self.scale))

    def report_callback_exception(self, exc, val, tb):
        """Show unexpected errors: the .exe has no console, so Tk's default printout is lost."""
        detail = "".join(traceback.format_exception(exc, val, tb)).rstrip()
        if sys.stderr:
            print(detail, file=sys.stderr)
        try:
            self.log("Unexpected error:\n" + detail)
        except Exception:                              # the Activity log isn't built yet
            pass
        key = (exc, str(val))
        if self._error_open or key in self._errors_shown:
            return                       # e.g. failing in a redraw: logged, but only one dialog
        self._errors_shown.add(key)
        self._error_open = True
        try:
            messagebox.showerror("Unexpected error",
                                 f"{exc.__name__}: {val}\n\nThe full details are in the Activity "
                                 "log on the Overview tab.", parent=self)
        finally:
            self._error_open = False

    # ── look ──
    def _style(self):
        base = tkfont.nametofont("TkDefaultFont")
        if sys.platform == "win32":
            base.configure(family="Segoe UI")
        if sys.platform != "darwin":
            base.configure(size=10)
        for name in ("TkTextFont", "TkMenuFont"):
            tkfont.nametofont(name).configure(family=base.actual("family"), size=base.actual("size"))
        title = base.copy()
        title.configure(size=base.actual("size") + 4, weight="bold")
        strong = base.copy()
        strong.configure(weight="bold")
        self._fonts = (title, strong)                 # keep references alive
        px = self.px

        # classic-Tk parts that ttk styles don't reach (combobox drop-down list, dialogs)
        self.option_add("*TCombobox*Listbox.font", base)
        self.option_add("*TCombobox*Listbox.background", RAISED)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", SELECT)
        self.option_add("*TCombobox*Listbox.selectForeground", FG)
        self.option_add("*TCombobox*Listbox.borderWidth", 0)

        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=base, bordercolor=LINE,
                    lightcolor=BG, darkcolor=BG, troughcolor=BG, focuscolor=BG,
                    selectbackground=SELECT, selectforeground=FG, insertcolor=FG,
                    fieldbackground=PANEL)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=LINE)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("Dim.TLabel", foreground=DIM)
        s.configure("Accent.TLabel", foreground=ACCENT)
        s.configure("Bad.TLabel", foreground=BAD)
        s.configure("Good.TLabel", foreground=GOOD)
        s.configure("Title.TLabel", font=title)
        s.configure("Head.TLabel", foreground=MUTED, font=strong)

        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0),
                    bordercolor=BG, lightcolor=BG, darkcolor=BG)
        s.configure("TNotebook.Tab", background=BG, foreground=MUTED, borderwidth=0, bordercolor=BG,
                    padding=(px(16), px(8)), lightcolor=BG, darkcolor=BG)
        s.map("TNotebook.Tab", foreground=[("selected", ACCENT), ("active", FG)],
              background=[("selected", BG)], bordercolor=[("selected", BG)],
              lightcolor=[("selected", BG)], padding=[("selected", (px(16), px(8)))],
              expand=[("selected", (0, 0, 0, 0))])

        s.configure("TButton", background=RAISED, foreground=FG, bordercolor=LINE, lightcolor=RAISED,
                    darkcolor=RAISED, padding=(px(12), px(5)), relief="flat", width=0)
        s.map("TButton", background=[("disabled", BG), ("pressed", LINE), ("active", HOVER)],
              lightcolor=[("active", HOVER)], darkcolor=[("active", HOVER)],
              foreground=[("disabled", DIM)], bordercolor=[("disabled", LINE)])
        s.configure("Accent.TButton", background=ACCENT, foreground=ON_ACCENT, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT)
        s.map("Accent.TButton", background=[("pressed", ACCENT_DARK), ("active", ACCENT_DARK)],
              lightcolor=[("active", ACCENT_DARK)], darkcolor=[("active", ACCENT_DARK)],
              bordercolor=[("active", ACCENT_DARK)])

        for widget in ("TEntry", "TCombobox"):
            s.configure(widget, fieldbackground=PANEL, background=RAISED, foreground=FG,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=px(5),
                        arrowcolor=MUTED, insertcolor=FG)
            s.map(widget, bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)],
                  darkcolor=[("focus", ACCENT)])
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", FG)],
              background=[("active", HOVER)], arrowcolor=[("active", FG)])

        s.configure("TCheckbutton", background=BG, foreground=FG, indicatorbackground=PANEL,
                    indicatorforeground=ACCENT, indicatormargin=(0, 0, px(6), 0))
        s.map("TCheckbutton", background=[("active", BG)],
              indicatorbackground=[("selected", PANEL), ("active", RAISED)])

        s.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        s.configure("Vertical.TScrollbar", background="#3a404c", troughcolor=PANEL, bordercolor=PANEL,
                    lightcolor="#3a404c", darkcolor="#3a404c", relief="flat", arrowsize=px(11),
                    gripcount=0)
        s.map("Vertical.TScrollbar", background=[("active", "#4a5160")],
              lightcolor=[("active", "#4a5160")], darkcolor=[("active", "#4a5160")])

        row_h = base.metrics("linespace") + px(11)
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG,
                    borderwidth=0, rowheight=row_h)
        s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", FG)])
        s.configure("Treeview.Heading", background=RAISED, foreground=MUTED, relief="flat",
                    borderwidth=0, padding=(px(8), px(6)), lightcolor=RAISED, darkcolor=RAISED,
                    bordercolor=RAISED)
        s.map("Treeview.Heading", background=[("active", HOVER)])
        s.layout("Side.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.configure("Side.Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG,
                    borderwidth=0, rowheight=base.metrics("linespace") + px(15), indent=0)
        s.map("Side.Treeview", background=[("selected", SELECT)], foreground=[("selected", ACCENT)])

    # ── layout ──
    def _build(self):
        px = self.px
        top = ttk.Frame(self, padding=(px(16), px(14), px(16), px(6)))
        top.pack(fill="x")
        ttk.Label(top, text="Config folder", style="Muted.TLabel").pack(side="left")
        self.path_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.path_var)
        entry.pack(side="left", fill="x", expand=True, padx=px(8))
        entry.bind("<Return>", lambda _e: self.load(self.path_var.get()))
        ttk.Button(top, text="Browse…", command=self.browse).pack(side="left")
        ttk.Button(top, text="Reload", command=lambda: self.load(self.path_var.get())
                   ).pack(side="left", padx=(px(6), px(24)))
        ttk.Button(top, text="Resolve conflicts", command=self.resolve).pack(side="left")
        ttk.Button(top, text="Save changes", style="Accent.TButton",
                   command=self.save).pack(side="left", padx=(px(6), 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=px(16), pady=(px(4), 0))
        self.overview = ttk.Frame(self.notebook, padding=(0, px(14), 0, 0))
        self.priorities = PrioritiesView(self)
        self.shared = SettingsView(self, lambda: self.ws.shared, "Area", lambda s: s.domain)
        self.unique = SettingsView(self, lambda: self.ws.unique, "Mod", lambda s: s.mod)
        for tab, name in ((self.overview, "Overview"), (self.priorities, "Priorities"),
                          (self.shared, "Shared"), (self.unique, "Unique")):
            self.notebook.add(tab, text=name)
        self._build_overview()
        self.priorities.rebuild()

        bar = ttk.Frame(self, padding=(px(16), px(6), px(16), px(10)))
        bar.pack(fill="x")
        self.status, self.unsaved = tk.StringVar(), tk.StringVar()
        ttk.Label(bar, textvariable=self.status, style="Muted.TLabel").pack(side="left")
        ttk.Label(bar, textvariable=self.unsaved, style="Accent.TLabel").pack(side="right")

    def _build_overview(self):
        px, tab = self.px, self.overview
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=(0, px(10)))
        ttk.Label(bar, text=f"Fabric {GAME_VERSION}", style="Muted.TLabel").pack(side="left")
        self.btn_updates = ttk.Button(bar, text="Check for updates", command=self.check_updates)
        self.btn_updates.pack(side="right")

        cols = (("mod", "Mod", 120, "w", False), ("config", "Config file", 300, "w", True),
                ("settings", "Settings", 80, "e", False), ("shared", "Shared", 70, "e", False),
                ("conflicts", "Conflicts", 80, "e", False), ("installed", "Installed", 160, "w", False),
                ("latest", "Latest for " + GAME_VERSION, 170, "w", False))
        card = ttk.Frame(tab, style="Card.TFrame", padding=1)
        card.pack(fill="x")
        self.ov = ttk.Treeview(card, columns=[c[0] for c in cols], show="headings",
                               height=len(MODS), selectmode="none")
        for key, title, width, anchor, stretch in cols:
            self.ov.heading(key, text=title, anchor=anchor)
            self.ov.column(key, width=px(width), minwidth=px(60), stretch=stretch, anchor=anchor)
        self.ov.tag_configure("dim", foreground=DIM)
        self.ov.tag_configure("new", foreground=NEW)
        for name in MODS:
            self.ov.insert("", "end", iid=name, tags=("dim",), values=(name, "—", "—", "—", "—", "—", "—"))
        self.ov.pack(fill="x")

        ttk.Label(tab, text="Activity", style="Muted.TLabel").pack(anchor="w", pady=(px(18), px(6)))
        card = ttk.Frame(tab, style="Card.TFrame", padding=1)
        card.pack(fill="both", expand=True)
        self.activity = tk.Text(card, height=7, wrap="word", relief="flat", background=PANEL,
                                foreground=MUTED, padx=px(10), pady=px(8), state="disabled",
                                highlightthickness=0, borderwidth=0, insertbackground=FG,
                                selectbackground=SELECT, selectforeground=FG,
                                font=tkfont.nametofont("TkFixedFont"))
        self.activity.pack(fill="both", expand=True)

    # ── status / log ──
    def say(self, msg):
        self.status.set(msg)

    def log(self, msg):
        self.activity.configure(state="normal")
        self.activity.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def note(self, msg):
        self.say(msg)
        self.log(msg)

    def after_change(self):
        n = len(self.ws.changed)
        self.unsaved.set(plural(n, "unsaved change") if n else "")
        counts = self.ws.conflicts()                 # one pass, shared by both views
        self.update_overview(counts)
        self.priorities.update_view(counts)

    def _config_text(self, m):
        if m.files:
            first = m.files[0].path
            try:
                rel = first.relative_to(self.ws.folder).as_posix()
            except ValueError:
                rel = first.name
            return rel + (f"  (+{len(m.files) - 1} more)" if len(m.files) > 1 else "")
        return "unreadable: " + m.errors[0] if m.errors else "not found"

    def update_overview(self, counts=None):
        by_mod, _, _ = counts or self.ws.conflicts()
        for name in MODS:
            m = self.ws.mods.get(name) or ModInfo(name)
            latest = m.latest[0] if m.latest else "—"
            tag = ("new",) if m.latest and m.latest[1] == "new" else (() if m.loaded else ("dim",))
            self.ov.item(name, tags=tag, values=(
                name, self._config_text(m), f"{len(m.settings):,}" if m.loaded else "—",
                m.shared if m.loaded else "—", by_mod.get(name, 0) if m.loaded else "—",
                m.installed or "not installed", latest))

    # ── actions ──
    def browse(self):
        p = filedialog.askdirectory(parent=self, title="Select your Minecraft config folder",
                                    initialdir=self.path_var.get() or str(Path.home()))
        if p:
            self.load(p)

    def load(self, folder):
        folder = folder.strip().strip('"')
        if not folder:
            return self.say("Choose your Minecraft config folder to begin.")
        if self.ws.changed and not messagebox.askyesno(
                "Unsaved changes", "Reloading discards your unsaved changes. Continue?", parent=self):
            return
        t0 = time.perf_counter()
        try:
            self.ws.load(folder)
        except OSError as e:
            return messagebox.showerror("Can't open folder", str(e), parent=self)
        self.path_var.set(str(self.ws.folder))
        self.prefs["config_dir"] = str(self.ws.folder)
        save_prefs(self.prefs)
        for name, (version, jar) in installed_jars(self.ws.folder.parent / "mods").items():
            self.ws.mods[name].installed, self.ws.mods[name].jar = version, jar
        found = [m for m in self.ws.mods.values() if m.loaded]
        for m in self.ws.mods.values():
            for err in m.errors:
                self.log(f"{m.name}: could not read {err}")
        self.shared.set_groups(list(self.ws.choices))
        self.unique.set_groups([m.name for m in found])
        self.shared.reset()
        self.unique.reset()
        self.shared.refresh()
        self.unique.refresh()
        if self.priorities.area not in self.ws.choices and self.ws.choices:
            self.priorities.area = next(iter(self.ws.choices))
        self.priorities.rebuild()
        self.after_change()
        self.note(f"Loaded {len(self.ws.settings):,} settings from {plural(len(found), 'mod')} "
                  f"in {time.perf_counter() - t0:.2f}s.")

    def _remember_priorities(self):
        self.prefs["priority"] = dict(self.ws.priority)
        self.prefs["overrides"] = dict(self.ws.overrides)
        save_prefs(self.prefs)
        self.shared.refresh()
        self.after_change()

    def set_priority(self, area, mod):
        self.ws.set_priority(area, mod)
        self._remember_priorities()
        self.note(f"{mod} now has priority for {area}.")

    def set_override(self, feature_key, mod):
        self.ws.set_override(feature_key, mod)
        self._remember_priorities()
        # Look the name up: area names can contain "/" themselves ("GUI/HUD").
        name = next((f.name for f in self.ws.features if f.key == feature_key), feature_key)
        self.note(f"{name}: " + ("follows the area choice." if mod is None else
                                 "off in every mod." if mod == OFF else f"uses {mod}."))

    def apply(self, s, value):
        self.ws.set_value(s, value)
        self.shared.paint(s)
        self.unique.paint(s)
        self.after_change()
        self.say(f"{s.mod} › {s.label} set to {fmt(value)}. Not saved yet.")

    def ask_value(self, s):
        """Show the edit dialog; returns the parsed value or None if cancelled."""
        dlg = EditDialog(self, s)
        self.wait_window(dlg)
        return dlg.result

    def edit_setting(self, s):
        if isinstance(s.value, bool):
            return self.apply(s, not s.value)
        value = self.ask_value(s)
        if value is not None and not same(value, s.value):
            self.apply(s, value)

    def resolve(self, area=None):
        n = self.ws.resolve(area)
        if not n:
            return self.say("No conflicts to resolve.")
        self.shared.refresh()
        self.unique.refresh()
        self.after_change()
        where = f" in {area}" if area else ""
        self.note(f"Applied {plural(n, 'recommended value')}{where}. Save to keep them.")

    def save(self):
        files = self.ws.dirty_files()
        if not files:
            return self.say("Nothing to save.")
        risky = [cf.path.name for cf in files if cf.comments and not cf.warned]
        if risky and not messagebox.askyesno(
                "Comments will be removed",
                "These files contain comments, which can't be kept when saving:\n\n  "
                + "\n  ".join(risky) + "\n\nA backup of each original is kept. Save anyway?",
                parent=self):
            return
        for cf in files:
            cf.warned = True
        saved, errors = self.ws.save()
        self.after_change()
        if saved:
            self.note(f"Saved {plural(len(saved), 'file')} ({', '.join(saved)}). "
                      "Originals are kept as .bak_* files.")
        if errors:
            for e in errors:
                self.log(f"Could not save {e}")
            messagebox.showerror("Some files weren't saved", "\n".join(errors), parent=self)

    def on_close(self):
        if self.ws.changed and not messagebox.askyesno(
                "Unsaved changes", f"Quit and discard {plural(len(self.ws.changed), 'unsaved change')}?",
                parent=self):
            return
        self.destroy()

    # ── update check (background thread, results handed over through a queue) ──
    def check_updates(self):
        jars = {m.name: (m.installed, m.jar) for m in self.ws.mods.values() if m.jar}
        if not jars:
            return self.say("No mod jars found next to the config folder (../mods).")
        self.btn_updates.state(["disabled"])
        self.say(f"Checking Modrinth for Fabric {GAME_VERSION} builds…")
        threading.Thread(target=self._update_worker, args=(jars,), daemon=True).start()
        self.after(150, self._poll)

    def _update_worker(self, jars):
        try:
            self._queue.put(("result", modrinth_status(jars)))
        except Exception as e:                       # network, JSON or API-shape problems
            self._queue.put(("error", f"{type(e).__name__}: {e}"))

    def _poll(self):
        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            return self.after(150, self._poll)
        self.btn_updates.state(["!disabled"])
        if kind == "error":
            self.log(f"Update check failed: {payload}")
            return self.say("Update check failed; see Activity.")
        for name, result in payload.items():
            if name in self.ws.mods:
                self.ws.mods[name].latest = result
        self.update_overview()
        new = [n for n, (_t, state) in payload.items() if state == "new"]
        failed = [n for n, (_t, state) in payload.items() if state == "failed"]
        parts = [f"Updates available for {', '.join(new)}."] if new else []
        if failed:
            parts.append(f"Couldn't check {', '.join(failed)}; try again later.")
        self.note(" ".join(parts) or f"Everything installed is up to date for Fabric {GAME_VERSION}.")


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)       # crisp text on high-DPI screens
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
