"""Checks hd-seed-search output against SpecsHD's seed_search.csv.

usage:
  compare.py pick <seed_search.csv> <count> <seeds.txt>
      Writes the first <count> seeds that have results for every checked column.
  compare.py check <seed_search.csv> <out.jsonl>
      Compares hd-seed-search's levels with the seed search results.
"""

import csv
import json
import pathlib
import re
import sys

HD_CPP = pathlib.Path(__file__).parent / "../3rdparty/HDDLL/src/hd.cpp"


def load_entity_names():
    source = HD_CPP.read_text(encoding="utf-8")
    body = source[source.index("const char *EntityTypeName("):]
    body = body[: body.index("default:")]
    return {int(n): name for n, name in re.findall(r'case (\d+):\s*return "([^"]*)";', body)}


NAMES = load_entity_names()


def names(types):
    return ";".join(NAMES.get(t, "Unknown") for t in types) or "none"


def level_name(level):
    return f"{(level - 1) // 4 + 1}-{(level - 1) % 4 + 1}"


MYSTERY_BOX = 248


# Each works out a seed search column from hd-seed-search's levels the way the
# preset in SpecsHD's seeded_mode.cpp does, or None without the levels for it


def mines_eggy(levels):
    # Mystery Box for sale and a Kali altar on the same level
    if not all(lvl in levels for lvl in (2, 3, 4)):
        return None
    matched = [level_name(lvl) for lvl in (2, 3, 4)
               if MYSTERY_BOX in levels[lvl]["shop"] and levels[lvl]["altar"]]
    return ";".join(matched) or "false"


def worm(level):
    def preset(levels):
        if level not in levels:
            return None
        lvl = levels[level]
        return "true" if lvl["damsel"] and lvl["wormTongue"] else "false"
    return preset


def low_percent_bm(levels):
    # Only one BM spawns a run, so the first level with one decides it
    if not all(lvl in levels for lvl in (5, 6, 7)):
        return None
    for lvl in (5, 6, 7):
        bm = levels[lvl]["blackMarket"]
        if bm:
            good = bm["pathRoom"] and bm["emptyNeighbours"] >= 2
            return level_name(lvl) if good else "false"
    return "false"


def altar_moai(levels):
    if mines_eggy(levels) == "false":
        return "n/a"
    if not all(lvl in levels for lvl in (9, 10, 11)):
        return None
    # The first level with the moai decides it, and one on 3-1 doesn't count
    for lvl in (9, 10, 11):
        if levels[lvl]["moai"]:
            return level_name(lvl) if lvl >= 10 and levels[lvl]["altar"] else "false"
    return "false"


def path_anubis(levels):
    if low_percent_bm(levels) == "false":
        return "n/a"
    if 13 not in levels:
        return None
    anubis = levels[13]["anubis"]
    if not anubis:
        return "n/a"
    return "true" if any(anubis) else "false"


COLUMNS = {
    "1-1 crate contents": lambda levels: names(levels[1]["crates"]) if 1 in levels else None,
    "1-2 shop items": lambda levels: names(levels[2]["shop"]) if 2 in levels else None,
    "1-3 shop items": lambda levels: (
        None if 3 not in levels
        else names(levels[3]["shop"]) if levels[3]["shopkeeper"] else "n/a"),
    "mines eggy": mines_eggy,
    "jungle worm": worm(5),
    "ice caves worm": worm(9),
    "low% bm": low_percent_bm,
    "altar+moai": altar_moai,
    "path anubis": path_anubis,
}


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {int(row["seed"]): row for row in csv.DictReader(f)}


def pick(csv_path, count, seeds_path):
    rows = load_csv(csv_path)
    seeds = [seed for seed, row in rows.items() if all(row.get(col) for col in COLUMNS)]
    pathlib.Path(seeds_path).write_text("\n".join(map(str, seeds[:count])) + "\n")
    print(f"wrote {min(count, len(seeds))} of {len(seeds)} usable seeds")


def same_items(a, b):
    """Lists of the same items in any order. The seed search reads entities
    after the level's first update, which can reorder the active list."""
    return sorted(a.split(";")) == sorted(b.split(";"))


def check(csv_path, out_path):
    rows = load_csv(csv_path)
    # column -> [same order, same items in another order, different]
    results = {col: [0, 0, 0] for col in COLUMNS}
    mismatches = []
    unknown = 0

    for line in open(out_path, encoding="utf-8"):
        generated = json.loads(line)
        row = rows.get(generated["seed"])
        if row is None:
            unknown += 1
            continue
        levels = {lvl["level"]: lvl for lvl in generated["levels"]}
        for col, value in COLUMNS.items():
            expected = row.get(col)
            actual = value(levels)
            if not expected or actual is None:
                continue
            if actual == expected:
                results[col][0] += 1
            elif same_items(actual, expected):
                results[col][1] += 1
            else:
                results[col][2] += 1
                if len(mismatches) < 15:
                    mismatches.append((generated["seed"], col, expected, actual))

    for col, (exact, reordered, wrong) in results.items():
        total = exact + reordered + wrong
        print(f"{col:20s} {exact + reordered:6d}/{total:<6d} same items "
              f"({exact} in the same order), {wrong} different")
    if unknown:
        print(f"{unknown} seeds weren't in the csv")
    for seed, col, expected, actual in mismatches:
        print(f"  seed {seed} {col}: expected {expected!r}, got {actual!r}")
    return all(wrong == 0 for _, _, wrong in results.values())


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "pick":
        pick(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif len(sys.argv) == 4 and sys.argv[1] == "check":
        sys.exit(0 if check(sys.argv[2], sys.argv[3]) else 1)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
