"""Pure presentation helpers for the existing DBF benchmark evidence."""

from collections import defaultdict
from html import escape
from math import isfinite
from statistics import median

PHASES = {
    "dbf_to_arrow": "DBF → Arrow · parsing",
    "dbc_to_parquet": "DBC → Parquet · com descompactação",
    "dbf_to_parquet": "DBF → Parquet · sem descompactação",
    "lake_publication": "Publicação · lake novo, dados preparados",
}
METRICS = {
    "Tempo (ms)": "time_ms",
    "Memória RSS (MiB)": "rss_mib",
    "Disco temporário (MiB)": "disk_mib",
}
COLORS = {"python": "#2563eb", "rust": "#c2410c"}


def measurement_rows(report):
    """Read measured rounds only; refuse unfinished or inconsistent evidence."""
    if not report.get("completed") or report.get("comparison") != "backends":
        raise ValueError("É necessário um relatório concluído de comparação entre backends.")
    rows = []
    for case in report["cases"]:
        for phase in case["phases"]:
            if not phase["equivalent"]:
                raise ValueError("O relatório contém resultados não equivalentes.")
            for backend in COLORS:
                runs = [r for r in phase["runs"] if r["mode"] == backend]
                if len(runs) != report["rounds"] or len({r["round"] for r in runs}) != len(runs):
                    raise ValueError("Rodadas ausentes ou duplicadas no relatório.")
                for run in runs:
                    if not run["matches_reference"]:
                        raise ValueError("Uma rodada não corresponde à referência.")
                    values = [
                        run[k]
                        for k in ("seconds", "peak_rss_bytes", "peak_temp_disk_bytes_sampled")
                    ]
                    if any(not isfinite(v) or v < 0 for v in values) or values[0] == 0:
                        raise ValueError("Medição inválida no relatório.")
                    rows.append(
                        {
                            "corpus": case["corpus"],
                            "dataset": case["dataset"],
                            "amplified": case["amplified"],
                            "phase": phase["phase"],
                            "backend": backend,
                            "round": run["round"] + 1,
                            "rows": run["rows"],
                            "time_ms": run["seconds"] * 1000,
                            "rss_mib": run["peak_rss_bytes"] / 2**20,
                            "disk_mib": run["peak_temp_disk_bytes_sampled"] / 2**20,
                        }
                    )
    if not rows:
        raise ValueError("O relatório não contém medições.")
    return rows


def comparison_rows(rows):
    """Recompute medians from measured runs, without averaging speedup ratios."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["corpus"], row["phase"]].append(row)
    result = []
    for (corpus, phase), group in groups.items():
        by_backend = {b: [r for r in group if r["backend"] == b] for b in COLORS}
        times = {b: median(r["time_ms"] for r in runs) for b, runs in by_backend.items()}
        rss = {b: median(r["rss_mib"] for r in runs) for b, runs in by_backend.items()}
        result.append(
            {
                "corpus": corpus,
                "phase": phase,
                "amplified": group[0]["amplified"],
                "rows": group[0]["rows"],
                "python_ms": times["python"],
                "rust_ms": times["rust"],
                "speedup": times["python"] / times["rust"],
                "rss_ratio": rss["rust"] / rss["python"] if rss["python"] else None,
            }
        )
    return result


def measurement_svg(rows, metric, title, unit):
    """Median bars and individual rounds on a common linear, zero-based scale."""
    maximum = max((r[metric] for r in rows), default=0) or 1
    scale = 610 / maximum
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 245" '
        f'role="img" aria-label="{escape(title, quote=True)}" style="width:100%;max-width:1000px">',
        f"<title>{escape(title)}</title>",
        '<rect width="900" height="245" rx="12" fill="#f8fafc"/>',
        f'<text x="24" y="30" fill="#0f172a" font-size="18">{escape(title)} · {escape(unit)}</text>',
    ]
    for i in range(5):
        x = 125 + i * 610 / 4
        svg.append(f'<path d="M{x} 50V190" stroke="#cbd5e1"/>')
        svg.append(
            f'<text x="{x}" y="212" text-anchor="middle" font-size="12" fill="#475569">{maximum * i / 4:.2f}</text>'
        )
    for i, (backend, color) in enumerate(COLORS.items()):
        values = [r[metric] for r in rows if r["backend"] == backend]
        y = 80 + i * 72
        med = median(values)
        svg.append(
            f'<text x="24" y="{y + 6}" font-size="16" fill="#0f172a">{backend.title()}</text>'
        )
        svg.append(
            f'<rect x="125" y="{y - 14}" width="{med * scale}" height="28" rx="3" fill="{color}" fill-opacity="0.28"/>'
        )
        for j, value in enumerate(values):
            svg.append(
                f'<circle cx="{125 + value * scale}" cy="{y + (j % 3 - 1) * 5}" r="4" fill="{color}"><title>Rodada {j + 1}: {value:.3f} {escape(unit)}</title></circle>'
            )
        svg.append(f'<text x="760" y="{y + 5}" font-size="15" fill="{color}">{med:.3f}</text>')
    svg.append(
        '<text x="24" y="235" font-size="12" fill="#475569">Barra = mediana · pontos = rodadas medidas · menor é melhor</text></svg>'
    )
    return "".join(svg)
