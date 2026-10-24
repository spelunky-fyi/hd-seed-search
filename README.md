# hd-seed-search

Generates Spelunky HD levels for seeds without playing the game, using the
game's own level generation code, so the levels are exactly what the game
makes. It's what [HD Toolbox](https://github.com/spelunky-fyi/HD-Toolbox)'s
Seed Search tab runs, and the Toolbox bundles it from this repo's releases.

`hd-seed-search.exe` starts `Spelunky.exe` suspended with
`hd-seed-search-hook.dll` loaded. The game starts up as normal with its window
hidden, its sound off and Steam never started (about 2 seconds), and the hook
takes over where the main loop would start. For each seed it resets the run
and calls the game's level setup for each level, with no gameplay frames or
rendering in between, writes what it found and exits.

Because Steam is never started, Steam doesn't see the game as running (so
launching the real game still works) and the account's stats and
achievements can't be touched. The game runs in a job, so stopping
`hd-seed-search.exe` stops it too, and the Toolbox's process lookup ignores it.

Levels are seeded the same way as SpecsHD's seeded mode, so the results match
its seed search.

## Building

Requires CMake and Visual Studio (MSVC). It has to be 32-bit like the game.
HDDLL is a submodule, only for its headers.

```bash
git submodule update --init
cmake -A Win32 -S . -B build
cmake --build build --config Release
```

builds `build/Release/hd-seed-search.exe` and `hd-seed-search-hook.dll`.

## Releasing

Pushing a `v*` tag builds both files and attaches them to a GitHub release.
HD Toolbox pins the version it downloads in `scripts/fetch-seed-search.mjs`.

## Running it by itself

```bash
build/Release/hd-seed-search.exe seeds.txt out.jsonl 13
```

- `seeds.txt` has one seed per line.
- `13` is how many levels to generate per seed (default 3, at most 20).
- An optional 4th argument is the Spelunky folder, if it's not in the default
  Steam location.

`out.jsonl` gets one line per seed as each is generated, with each level's
layout (room types, entrance and exit rooms) and the things the seed search
looks for: crate contents, shop items, a prize wheel's prize, shopkeeper,
altar, damsel, worm tongue, moai, the black market entrance and Anubis.
`out.jsonl.log` has timings and any crash.

Setting `SEED_SEARCH_ENTITIES=1` also lists every active entity on each level
as `[type, kind, x, y, shop item, z depth]`, for working out what to look for.

## Tools

Python scripts for development. Neither is needed to build or run it.

- `tools/compare.py` checks the output against a SpecsHD `seed_search.csv`.
- `tools/entity_names.py` regenerates HD Toolbox's entity name table from
  HDDLL.

## Limits

- Windows only, and needs the Steam version of `Spelunky.exe` the offsets are
  for. The hook checks the bytes it patches and stops on a different exe.
- Levels are generated as a run that takes no special exits (worm, black
  market, mothership, ...).
