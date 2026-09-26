"""Generate the LaTeX tables the IAC paper takes from the database.

    python make_paper_tables.py

Writes outputs/tab_database.tex, outputs/tab_fractions.tex and
outputs/tab_completeness.tex. Every number in the paper's database
subsection comes from here, so the paper and data/vehicles.csv cannot drift
apart silently. Re-run after editing the database and copy the three files
next to main.tex, which pulls them in with \\input.

The synthetic demo entry is excluded everywhere. It exists to exercise the
Level B reconstruction path and it is not evidence about anything.
"""

import csv
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
SYNTHETIC = "SYNTHETIC_DEMO"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def total_mass(r):
    return num(r["gross_mass_kg"]) or num(r["mass_kg"])


def tex(s):
    """Escape the characters that actually appear in this database."""
    return (str(s).replace("\\", "/").replace("&", "\\&").replace("%", "\\%")
            .replace("_", "\\_").replace("#", "\\#"))


def short_name(name, limit=30):
    """Trim an ALREADY ESCAPED name to fit the table, on a word boundary.

    Takes escaped text so the ellipsis it appends survives, and trailing
    backslashes are trimmed so a cut can never land inside an escape.
    """
    if len(name) <= limit:
        return name
    cut = name[:limit].rsplit(" ", 1)[0].rstrip("\\")
    return cut + "\\ldots"


def fmt(v, places=1):
    return "--" if v is None else ("%.*f" % (places, v))


def load():
    with open(os.path.join(HERE, "data", "vehicles.csv")) as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["source_id"] != SYNTHETIC]


def fractions(rows, column):
    """{architecture: [(system_id, percent), ...]} for entries with both masses."""
    out = {}
    for r in rows:
        t, m = total_mass(r), num(r[column])
        if t and m is not None and t > 0:
            out.setdefault(r["architecture"], []).append((r["system_id"], 100.0 * m / t))
    return out


def stat_row(label, values):
    """label is trusted LaTeX written here, not database text, so not escaped."""
    return "%s & %d & %s & %s & %s to %s \\\\" % (
        label, len(values), fmt(st.median(values)), fmt(st.mean(values)),
        fmt(min(values)), fmt(max(values)))


def table_census(rows):
    lines = [
        "\\begin{table*}[!ht]", "\\centering", "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\begin{tabular}{lllrrrrl}", "\\hline",
        "System & Domain & Mobility & $m_{tot}$ & $m_{mob}$ & $m_{pay}$ & $P$ & Source \\\\",
        " & & & kg & kg & kg & W & \\\\", "\\hline",
    ]
    for r in sorted(rows, key=lambda r: (r["architecture"], r["system_id"])):
        lines.append("%s & %s & %s & %s & %s & %s & %s & %s \\\\" % (
            short_name(tex(r["name"])), tex(r["domain"]), tex(r["architecture"]),
            fmt(total_mass(r)), fmt(num(r["mobility_mass_kg"]), 2),
            fmt(num(r["payload_mass_kg"]), 1), fmt(num(r["power_W"]), 0),
            tex(r["source_id"])))
    lines += [
        "\\hline", "\\end{tabular}",
        "\\caption{Vehicle database, %d entries. A dash means the field is not "
        "populated from an indexed source, not that the quantity is zero. "
        "Source identifiers resolve in \\texttt{sources.yaml}.}" % len(rows),
        "\\label{tab:database}", "\\end{table*}",
    ]
    return "\n".join(lines)


def table_fractions(rows):
    mob, pay = fractions(rows, "mobility_mass_kg"), fractions(rows, "payload_mass_kg")
    lines = [
        "\\begin{table}[!ht]", "\\centering", "\\small",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\begin{tabular}{lrrrr}", "\\hline",
        "Group & $n$ & Median & Mean & Range \\\\",
        " & & \\% & \\% & \\% \\\\", "\\hline",
        "\\multicolumn{5}{l}{\\textit{Mobility mass / total mass}} \\\\",
    ]
    for arch in sorted(mob):
        lines.append(stat_row("\\quad " + tex(arch), [v for _, v in mob[arch]]))
    lines.append(stat_row("\\quad all", [v for i in mob.values() for _, v in i]))
    lines.append("\\hline")
    lines.append("\\multicolumn{5}{l}{\\textit{Payload mass / total mass}} \\\\")
    for arch in sorted(pay):
        lines.append(stat_row("\\quad " + tex(arch), [v for _, v in pay[arch]]))
    lines.append(stat_row("\\quad all", [v for i in pay.values() for _, v in i]))
    lines += [
        "\\hline", "\\end{tabular}",
        "\\caption{Mass fractions derived from the database. Computed only "
        "where both masses are populated, so $n$ is far below the entry count "
        "and every row is a small sample.}",
        "\\label{tab:fractions}", "\\end{table}",
    ]
    return "\n".join(lines)


def table_completeness(rows):
    fields = [
        ("gross_mass_kg", "Total or gross mass"),
        ("mobility_mass_kg", "Mobility mass"),
        ("payload_mass_kg", "Payload mass"),
        ("power_W", "Power"),
        ("speed_mps", "Speed"),
        ("drum_diameter_m", "Drum diameter"),
        ("length_m", "Screw length"),
        ("pitch_m", "Pitch"),
        ("blade_height_m", "Blade height"),
        ("mu_drawbar", "Measured drawbar coefficient"),
    ]
    n = len(rows)
    lines = [
        "\\begin{table}[!ht]", "\\centering", "\\small",
        "\\begin{tabular}{lrr}", "\\hline",
        "Field & Populated & of %d \\\\" % n, "\\hline",
    ]
    for key, label in fields:
        lines.append("%s & %d & %d \\\\" % (
            tex(label), sum(1 for r in rows if num(r[key]) is not None), n))
    lines += [
        "\\hline", "\\end{tabular}",
        "\\caption{Database completeness. The geometry fields are the ones the "
        "terramechanics model needs, and they are the emptiest. This table is "
        "the data collection plan, in priority order from the bottom up.}",
        "\\label{tab:completeness}", "\\end{table}",
    ]
    return "\n".join(lines)


def print_paper_counts(rows):
    """Tables 3 and 4 of the IAC-26 paper, printed in the form the paper uses."""
    def has(r, key):
        return num(r[key]) is not None

    arch = {}
    for r in rows:
        arch[r["architecture"]] = arch.get(r["architecture"], 0) + 1
    print("\nTable 3 of the paper, inventory by architecture:")
    for a, n in sorted(arch.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-40s %3d" % (a, n))
    print("  %-40s %3d" % ("total, excluding the synthetic example", len(rows)))

    geometry = ("drum_diameter_m", "blade_height_m", "length_m", "pitch_m")
    checks = (
        ("at least one total-mass field",
         lambda r: has(r, "mass_kg") or has(r, "gross_mass_kg")),
        ("mobility mass", lambda r: has(r, "mobility_mass_kg")),
        ("payload mass", lambda r: has(r, "payload_mass_kg")),
        ("power", lambda r: has(r, "power_W")),
        ("speed", lambda r: has(r, "speed_mps")),
        ("drum diameter, blade height, length and lead together",
         lambda r: all(has(r, k) for k in geometry)),
        ("drawbar coefficient", lambda r: has(r, "mu_drawbar")),
    )
    print("\nTable 4 of the paper, populated records out of %d:" % len(rows))
    for label, test in checks:
        hits = [r["system_id"] for r in rows if test(r)]
        extra = "   " + ", ".join(hits) if len(hits) <= 3 else ""
        print("  %-55s %3d%s" % (label, len(hits), extra))


def main():
    rows = load()
    os.makedirs(OUT, exist_ok=True)
    header = ("% Generated by make_paper_tables.py from data/vehicles.csv.\n"
              "% Do not edit by hand. Re-run the script after changing "
              "the database.\n\n")
    for name, body in (("tab_database.tex", table_census(rows)),
                       ("tab_fractions.tex", table_fractions(rows)),
                       ("tab_completeness.tex", table_completeness(rows))):
        path = os.path.join(OUT, name)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(header + body + "\n")
        os.replace(tmp, path)
        print("wrote", os.path.relpath(path, HERE))

    print("\nnumbers quoted in the paper text:")
    for label, d in (("mobility", fractions(rows, "mobility_mass_kg")),
                     ("payload", fractions(rows, "payload_mass_kg"))):
        for arch in sorted(d):
            v = sorted(x for _, x in d[arch])
            print("  %-8s %-12s n=%d median %.1f range %.1f to %.1f"
                  % (label, arch, len(v), st.median(v), min(v), max(v)))

    print_paper_counts(rows)


if __name__ == "__main__":
    main()
