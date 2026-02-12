from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioRow:
    project: str
    area: str
    money: int
    urgency: int
    leverage: int
    strategic: int
    risk: int
    score: int
    status: str
    next_action: str
    owner: str


def compute_score(*, money: int, urgency: int, leverage: int, strategic: int, risk: int) -> int:
    return int(money) + int(urgency) + int(leverage) + int(strategic) - int(risk)


def _to_int(x: str | int | None) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        return 0


def parse_portfolio_markdown_table(md: str) -> list[PortfolioRow]:
    """Parse the markdown table from PORTFOLIO.md.

    Expected columns:
    Project | Area | MoneyPotential | Urgency | Leverage | StrategicValue | RiskPenalty | Score | Status | Next Action | Owner

    Tolerant parser: ignores non-table lines; skips separator row.
    """

    lines = [ln.strip() for ln in (md or "").splitlines() if ln.strip()]
    rows: list[PortfolioRow] = []

    # Find first header line that looks like a markdown table.
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("|") and ln.endswith("|") and "Project" in ln and "Status" in ln:
            header_idx = i
            break
    if header_idx is None:
        return []

    def split_row(ln: str) -> list[str]:
        parts = [p.strip() for p in ln.strip("|").split("|")]
        return parts

    headers = split_row(lines[header_idx])
    # Skip separator row if present
    data_lines = lines[header_idx + 2 :] if header_idx + 1 < len(lines) else []

    # Map known columns to indices (case-insensitive)
    ix: dict[str, int] = {h.strip().lower(): j for j, h in enumerate(headers)}

    def get(parts: list[str], key: str) -> str:
        j = ix.get(key)
        if j is None or j >= len(parts):
            return ""
        return parts[j].strip()

    for ln in data_lines:
        if not (ln.startswith("|") and ln.endswith("|")):
            continue
        parts = split_row(ln)
        project = get(parts, "project")
        if not project:
            continue

        area = get(parts, "area")
        money = _to_int(get(parts, "moneypotential"))
        urgency = _to_int(get(parts, "urgency"))
        leverage = _to_int(get(parts, "leverage"))
        strategic = _to_int(get(parts, "strategicvalue"))
        risk = _to_int(get(parts, "riskpenalty"))

        status = (get(parts, "status") or "").strip().upper() or "PAUSED"
        next_action = get(parts, "next action") or get(parts, "next action ") or get(parts, "nextaction")
        owner = get(parts, "owner")

        score_raw = get(parts, "score")
        score = _to_int(score_raw)
        if score == 0 and any([money, urgency, leverage, strategic, risk]):
            score = compute_score(money=money, urgency=urgency, leverage=leverage, strategic=strategic, risk=risk)

        rows.append(
            PortfolioRow(
                project=project,
                area=area,
                money=money,
                urgency=urgency,
                leverage=leverage,
                strategic=strategic,
                risk=risk,
                score=score,
                status=status,
                next_action=next_action,
                owner=owner,
            )
        )

    return rows


def pick_active_set(rows: list[PortfolioRow], *, min_n: int = 3, max_n: int = 7) -> list[PortfolioRow]:
    candidates = [r for r in rows if r.status != "DONE"]
    candidates.sort(key=lambda r: (r.score, r.urgency, r.money), reverse=True)
    n = max(min_n, min(max_n, len(candidates)))
    return candidates[:n]
