"""
Abstract: One-shot Pageviews-based Wikipedia candidate page selection.
Out of scope: Source-pipeline submission, card extraction, and taxonomy assignment.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import unquote
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENWIKI_ROOT = Path("/Volumes/WD-Black-4TB/data/enwiki")
DEFAULT_PREPROCESSED_ROOT = (
    DEFAULT_ENWIKI_ROOT / "enwiki-20260301-preprocessed" / "runs" / "run-00001"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "human_workspace" / "pageview-selection-output"
DEFAULT_USER_AGENT = (
    "KnowledgePageviewSelection/0.1 "
    "(https://knowledge.orbitalis.org; local one-shot candidate selection)"
)
TOP_ENDPOINT = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
    "{project}/{access}/{year}/{month}/all-days"
)
DENIED_NAMESPACES = {
    "Category",
    "File",
    "Help",
    "Portal",
    "Special",
    "Talk",
    "Template",
    "User",
    "Wikipedia",
}
DENIED_TITLE_PREFIXES = (
    "Deaths in ",
    "Index of ",
    "List of ",
    "Lists of ",
    "Timeline of ",
)
ENTERTAINMENT_PATTERNS = (
    re.compile(
        r"\([^)]*\b(?:film|film series|TV series|album|song|video game)\)$",
        re.IGNORECASE,
    ),
    re.compile(r"\bseason \d+\b", re.IGNORECASE),
    re.compile(r"^\d{4} in film$", re.IGNORECASE),
)
CURRENT_EVENT_PATTERN = re.compile(
    r"^20(?:2[0-6])_.+|^20(?:2[0-6]) .+|^20(?:2[0-6])$", re.IGNORECASE
)
BIOGRAPHY_NOISE_PATTERN = re.compile(
    r"\b(?:is|was|are|were) an? [^.]{0,100}\b("
    r"actor|actress|singer|rapper|musician|songwriter|television personality|"
    r"media personality|youtuber|streamer|model|politician|businessman|"
    r"businesswoman|political activist|professional wrestler|mixed martial artist|"
    r"film director|filmmaker|murderer|serial killer|sex offender|footballer|"
    r"basketball player|baseball player|baseball outfielder|baseball shortstop|"
    r"baseball infielder|baseball pitcher|baseball catcher|cricketer|"
    r"tennis player|golfer|boxer|quarterback|linebacker|wide receiver|"
    r"running back|ice hockey player|racing driver"
    r")\b",
    re.IGNORECASE,
)
ENTERTAINMENT_LEAD_PATTERN = re.compile(
    r"\b(?:is|was|are|were) an? [^.]{0,120}\b("
    r"film|television series|tv series|album|song|professional football club|"
    r"sports club|sports competition|wrestling event"
    r")\b",
    re.IGNORECASE,
)
ADULT_ENTERTAINMENT_LEAD_PATTERN = re.compile(
    r"\b("
    r"pornography website|pornographic website|pornographic video sharing website|"
    r"adult entertainment website|adult entertainment company|pornographic film|"
    r"adult film|anime and manga pornography"
    r")\b",
    re.IGNORECASE,
)
LOW_SIGNAL_LOCALITY_LEAD_PATTERN = re.compile(
    r"\b(?:is|was) an? (?:unincorporated community|census-designated place|"
    r"village|township)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class AggregatedPage:
    title: str
    total_views: int
    months_seen: int
    best_rank: int
    score: int


@dataclass(frozen=True, slots=True)
class ArticleRecord:
    page_id: int
    title: str
    url: str
    text_length: int
    lead_text: str = ""


@dataclass(frozen=True, slots=True)
class CandidateRow:
    selection_rank: int
    page_id: int
    title: str
    url: str
    total_views: int
    months_seen: int
    best_rank: int
    score: int
    text_length: int


def normalize_api_article_title(article: str) -> str:
    return unquote(article).replace("_", " ")


def reject_reason_for_title(title: str) -> str | None:
    if title == "Main Page":
        return "main_page"
    if title.startswith("."):
        return "low_signal_title"

    namespace, separator, _ = title.partition(":")
    if separator and namespace in DENIED_NAMESPACES:
        return "namespace"

    if title.startswith(DENIED_TITLE_PREFIXES):
        if title.startswith("Deaths in "):
            return "deaths"
        return "list"

    if CURRENT_EVENT_PATTERN.match(title):
        return "current_event_year"

    for pattern in ENTERTAINMENT_PATTERNS:
        if pattern.search(title):
            return "entertainment"

    return None


def reject_reason_for_article_record(article: ArticleRecord) -> str | None:
    if BIOGRAPHY_NOISE_PATTERN.search(article.lead_text):
        return "lead_biography_noise"
    if ENTERTAINMENT_LEAD_PATTERN.search(article.lead_text):
        return "lead_entertainment_noise"
    if ADULT_ENTERTAINMENT_LEAD_PATTERN.search(article.lead_text):
        return "lead_adult_entertainment_noise"
    if article.text_length < 5_000 and LOW_SIGNAL_LOCALITY_LEAD_PATTERN.search(article.lead_text):
        return "lead_low_signal_locality"
    return None


def aggregate_pageviews(
    month_payloads: dict[str, list[dict[str, Any]]],
    *,
    stable_month_bonus: int = 100_000,
) -> list[AggregatedPage]:
    total_views_by_title: dict[str, int] = defaultdict(int)
    months_by_title: dict[str, set[str]] = defaultdict(set)
    best_rank_by_title: dict[str, int] = {}

    for month, articles in month_payloads.items():
        seen_titles: set[str] = set()
        for article in articles:
            title = normalize_api_article_title(str(article["article"]))
            if title in seen_titles:
                continue
            seen_titles.add(title)
            views = int(article["views"])
            rank = int(article["rank"])
            total_views_by_title[title] += views
            months_by_title[title].add(month)
            current_best = best_rank_by_title.get(title)
            if current_best is None or rank < current_best:
                best_rank_by_title[title] = rank

    pages = [
        AggregatedPage(
            title=title,
            total_views=total_views,
            months_seen=len(months_by_title[title]),
            best_rank=best_rank_by_title[title],
            score=total_views + len(months_by_title[title]) * stable_month_bonus,
        )
        for title, total_views in total_views_by_title.items()
    ]
    return sorted(
        pages,
        key=lambda page: (
            -page.score,
            -page.months_seen,
            -page.total_views,
            page.best_rank,
            page.title,
        ),
    )


def canonicalize_aggregates(
    aggregates: list[AggregatedPage],
    redirect_map: dict[str, str],
    *,
    stable_month_bonus: int,
) -> list[AggregatedPage]:
    grouped: dict[str, list[AggregatedPage]] = defaultdict(list)
    for page in aggregates:
        grouped[redirect_map.get(page.title, page.title)].append(page)

    canonical_pages: list[AggregatedPage] = []
    for title, pages in grouped.items():
        total_views = sum(page.total_views for page in pages)
        months_seen = max(page.months_seen for page in pages)
        best_rank = min(page.best_rank for page in pages)
        canonical_pages.append(
            AggregatedPage(
                title=title,
                total_views=total_views,
                months_seen=months_seen,
                best_rank=best_rank,
                score=total_views + months_seen * stable_month_bonus,
            )
        )

    return sorted(
        canonical_pages,
        key=lambda page: (
            -page.score,
            -page.months_seen,
            -page.total_views,
            page.best_rank,
            page.title,
        ),
    )


def build_candidate_rows(
    aggregates: list[AggregatedPage],
    *,
    article_records: dict[str, ArticleRecord],
    disambiguation_titles: set[str],
    processed_page_ids: set[int],
    min_text_length: int,
    max_pages: int,
) -> tuple[list[CandidateRow], dict[str, int]]:
    summary: Counter[str] = Counter(total_input=len(aggregates))
    rows: list[CandidateRow] = []

    for page in aggregates:
        title_reject_reason = reject_reason_for_title(page.title)
        if title_reject_reason is not None:
            summary[f"rejected_{title_reject_reason}"] += 1
            continue
        if page.title in disambiguation_titles:
            summary["rejected_disambiguation"] += 1
            continue
        article = article_records.get(page.title)
        if article is None:
            summary["rejected_missing_article"] += 1
            continue
        if article.page_id in processed_page_ids:
            summary["rejected_processed"] += 1
            continue
        if article.text_length < min_text_length:
            summary["rejected_short_text"] += 1
            continue
        article_reject_reason = reject_reason_for_article_record(article)
        if article_reject_reason is not None:
            summary[f"rejected_{article_reject_reason}"] += 1
            continue

        rows.append(
            CandidateRow(
                selection_rank=len(rows) + 1,
                page_id=article.page_id,
                title=article.title,
                url=article.url,
                total_views=page.total_views,
                months_seen=page.months_seen,
                best_rank=page.best_rank,
                score=page.score,
                text_length=article.text_length,
            )
        )
        if len(rows) >= max_pages:
            break

    summary["selected"] = len(rows)
    return rows, dict(summary)


def latest_complete_month(today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    first_day_of_month = today.replace(day=1)
    last_complete_day = first_day_of_month - dt.timedelta(days=1)
    return last_complete_day.strftime("%Y-%m")


def month_window(*, end_month: str, count: int) -> list[str]:
    year, month = (int(part) for part in end_month.split("-", maxsplit=1))
    months: list[str] = []
    for offset in range(count - 1, -1, -1):
        absolute_month = year * 12 + (month - 1) - offset
        item_year = absolute_month // 12
        item_month = absolute_month % 12 + 1
        months.append(f"{item_year:04d}-{item_month:02d}")
    return months


def fetch_top_articles(
    *,
    project: str,
    access: str,
    year_month: str,
    user_agent: str,
    max_attempts: int = 3,
) -> list[dict[str, Any]]:
    year, month = year_month.split("-", maxsplit=1)
    url = TOP_ENDPOINT.format(
        project=project,
        access=access,
        year=year,
        month=month,
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Api-User-Agent": user_agent,
            "User-Agent": user_agent,
        },
    )
    last_error: HTTPError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return list(payload["items"][0]["articles"])
        except HTTPError as exc:
            last_error = exc
            if attempt == max_attempts or exc.code not in {404, 429, 500, 502, 503, 504}:
                break
            time.sleep(float(attempt))

    if last_error is not None:
        raise RuntimeError(f"failed to fetch {year_month}: HTTP {last_error.code}") from last_error
    raise RuntimeError(f"failed to fetch {year_month}")


def fetch_month_payloads(
    months: list[str],
    *,
    project: str,
    access: str,
    user_agent: str,
    request_delay_seconds: float,
    skip_missing_months: bool,
) -> dict[str, list[dict[str, Any]]]:
    payloads: dict[str, list[dict[str, Any]]] = {}
    for index, month in enumerate(months):
        print(f"fetching pageviews {month}...", file=sys.stderr, flush=True)
        try:
            payloads[month] = fetch_top_articles(
                project=project,
                access=access,
                year_month=month,
                user_agent=user_agent,
            )
        except RuntimeError as exc:
            if not skip_missing_months:
                raise
            print(f"warning: skipping {month}: {exc}", file=sys.stderr, flush=True)
        if index + 1 < len(months) and request_delay_seconds > 0:
            time.sleep(request_delay_seconds)
    if not payloads:
        raise RuntimeError("no Pageviews months were fetched")
    return payloads


def iter_jsonl_records(path: Path) -> Iterator[dict[str, Any]]:
    if path.suffix == ".zst":
        process = subprocess.Popen(
            ["zstdcat", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.stdout is None:
            raise RuntimeError(f"zstdcat stdout unavailable for {path}")
        for line in process.stdout:
            yield json.loads(line)
        _, stderr = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"zstdcat failed for {path}: {stderr.strip()}")
        return

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def iter_collection_shards(preprocessed_root: Path, collection: str) -> list[Path]:
    return sorted((preprocessed_root / collection).rglob("*.jsonl.zst"))


def load_disambiguation_titles(preprocessed_root: Path) -> set[str]:
    titles: set[str] = set()
    for path in iter_collection_shards(preprocessed_root, "disambiguation"):
        for record in iter_jsonl_records(path):
            titles.add(str(record["title"]))
    return titles


def load_redirect_map(
    preprocessed_root: Path,
    *,
    candidate_titles: set[str],
) -> dict[str, str]:
    redirect_map: dict[str, str] = {}
    if not candidate_titles:
        return redirect_map

    for path in iter_collection_shards(preprocessed_root, "redirect_aliases"):
        unresolved = candidate_titles - redirect_map.keys()
        if not unresolved:
            break
        for record in iter_jsonl_records(path):
            redirect_title = str(record["redirect_title"])
            if redirect_title in unresolved:
                redirect_map[redirect_title] = str(record["canonical_title"])
    return redirect_map


def load_article_records_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    titles: set[str],
) -> dict[str, ArticleRecord]:
    if not titles:
        return {}

    csv_payload = _build_copy_csv_payload(titles)
    sql = f"""
CREATE TEMP TABLE wanted_titles(title text primary key);
COPY wanted_titles(title) FROM STDIN WITH (FORMAT csv);
{csv_payload}\\.
SELECT json_build_object(
    'page_id', d.page_id,
    'title', d.title,
    'url', d.url,
    'text_length', char_length(d.clean_text),
    'lead_text', left(d.clean_text, 800)
)::text
FROM wikipedia.documents d
JOIN wanted_titles w ON w.title = d.title;
"""
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        postgres_user,
        "-d",
        postgres_db,
        "-v",
        "ON_ERROR_STOP=1",
        "-q",
        "-t",
        "-A",
    ]
    completed = subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"failed to query article records from corpus database: {completed.stderr.strip()}"
        )
    article_records: dict[str, ArticleRecord] = {}
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        payload = json.loads(stripped)
        article = ArticleRecord(
            page_id=int(payload["page_id"]),
            title=str(payload["title"]),
            url=str(payload["url"]),
            text_length=int(payload["text_length"]),
            lead_text=str(payload["lead_text"]),
        )
        article_records[article.title] = article
    return article_records


def load_processed_page_ids_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
) -> set[int]:
    command = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        postgres_user,
        "-d",
        postgres_db,
        "-q",
        "-t",
        "-A",
        "-c",
        "SELECT page_id FROM wikipedia.processed_documents;",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=True)
    return {int(line) for line in completed.stdout.splitlines() if line.strip()}


def _build_copy_csv_payload(values: set[str]) -> str:
    output = []
    for value in sorted(values):
        escaped = value.replace('"', '""')
        output.append(f'"{escaped}"\n')
    return "".join(output)


def write_outputs(
    *,
    output_dir: Path,
    rows: list[CandidateRow],
    summary: dict[str, int | str | list[str]],
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "selected_pageview_candidates.jsonl"
    csv_path = output_dir / "selected_pageview_candidates.csv"
    summary_path = output_dir / "selection_summary.json"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(asdict(row) for row in rows)

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return jsonl_path, csv_path, summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select one-shot Wikipedia page candidates from Pageviews top API."
    )
    parser.add_argument("--preprocessed-root", type=Path, default=DEFAULT_PREPROCESSED_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--project", default="en.wikipedia.org")
    parser.add_argument("--access", default="all-access")
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--end-month", default=latest_complete_month())
    parser.add_argument("--max-pages", type=int, default=9000)
    parser.add_argument("--min-text-length", type=int, default=1500)
    parser.add_argument("--stable-month-bonus", type=int, default=100_000)
    parser.add_argument("--request-delay-seconds", type=float, default=0.1)
    parser.add_argument(
        "--fail-on-missing-month",
        action="store_true",
        help="Abort instead of skipping a month whose top endpoint is unavailable.",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--postgres-container", default="knowledge-prod-knowledge_corpus_db-1")
    parser.add_argument("--postgres-user", default="knowledge_corpus_admin")
    parser.add_argument("--postgres-db", default="knowledge_corpus")
    parser.add_argument(
        "--skip-redirect-resolution",
        action="store_true",
        help="Do not scan local redirect alias shards for candidate title canonicalization.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    months = month_window(end_month=args.end_month, count=args.months)
    month_payloads = fetch_month_payloads(
        months,
        project=args.project,
        access=args.access,
        user_agent=args.user_agent,
        request_delay_seconds=args.request_delay_seconds,
        skip_missing_months=not args.fail_on_missing_month,
    )
    aggregates = aggregate_pageviews(
        month_payloads,
        stable_month_bonus=args.stable_month_bonus,
    )
    candidate_titles = {page.title for page in aggregates}

    redirect_map: dict[str, str] = {}
    if not args.skip_redirect_resolution:
        print("loading local redirect aliases...", file=sys.stderr, flush=True)
        redirect_map = load_redirect_map(args.preprocessed_root, candidate_titles=candidate_titles)
        aggregates = canonicalize_aggregates(
            aggregates,
            redirect_map,
            stable_month_bonus=args.stable_month_bonus,
        )
        candidate_titles = {page.title for page in aggregates}

    print("loading local disambiguation titles...", file=sys.stderr, flush=True)
    disambiguation_titles = load_disambiguation_titles(args.preprocessed_root)
    print("loading processed page ids...", file=sys.stderr, flush=True)
    processed_page_ids = load_processed_page_ids_from_docker(
        container=args.postgres_container,
        postgres_user=args.postgres_user,
        postgres_db=args.postgres_db,
    )
    print("loading article records from corpus database...", file=sys.stderr, flush=True)
    article_records = load_article_records_from_docker(
        container=args.postgres_container,
        postgres_user=args.postgres_user,
        postgres_db=args.postgres_db,
        titles=candidate_titles,
    )

    rows, counter_summary = build_candidate_rows(
        aggregates,
        article_records=article_records,
        disambiguation_titles=disambiguation_titles,
        processed_page_ids=processed_page_ids,
        min_text_length=args.min_text_length,
        max_pages=args.max_pages,
    )
    summary: dict[str, int | str | list[str]] = {
        **counter_summary,
        "months": months,
        "project": args.project,
        "access": args.access,
        "min_text_length": args.min_text_length,
        "max_pages": args.max_pages,
        "redirect_aliases_used": len(redirect_map),
        "article_records_loaded": len(article_records),
    }
    jsonl_path, csv_path, summary_path = write_outputs(
        output_dir=args.output_dir,
        rows=rows,
        summary=summary,
    )
    print(f"selected={len(rows)} jsonl={jsonl_path}")
    print(f"csv={csv_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
