"""
Abstract: Estimate pre-college STEM Wikipedia candidate pages from the corpus database.
Out of scope: Page orchestration, card extraction, and processed-document updates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg
from pydantic import Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_CORPUS_SRC = PROJECT_ROOT / "apps" / "knowledge_corpus" / "src"
HUMAN_WORKSPACE_DIR = PROJECT_ROOT / "human_workspace"
if str(KNOWLEDGE_CORPUS_SRC) not in sys.path:
    sys.path.insert(0, str(KNOWLEDGE_CORPUS_SRC))
if str(HUMAN_WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(HUMAN_WORKSPACE_DIR))

from knowledge_corpus.config import load_settings

from wiki_page_to_cards_types import PageRecord, StrictModel

DOMAIN_SEED_TITLES: dict[str, list[str]] = {
    "mathematics": [
        "Elementary algebra",
        "Algebraic expression",
        "Equation",
        "Linear equation",
        "Quadratic equation",
        "Inequality (mathematics)",
        "Polynomial",
        "Function (mathematics)",
        "Graph of a function",
        "Coordinate system",
        "Cartesian coordinate system",
        "Slope",
        "Line (geometry)",
        "Distance",
        "Midpoint",
        "Parabola",
        "Circle",
        "Angle",
        "Triangle",
        "Pythagorean theorem",
        "Similarity (geometry)",
        "Congruence (geometry)",
        "Trigonometric functions",
        "Sine",
        "Cosine",
        "Tangent",
        "Unit circle",
        "Law of sines",
        "Law of cosines",
        "Logarithm",
        "Exponentiation",
        "Sequence",
        "Arithmetic progression",
        "Geometric progression",
        "Complex number",
        "Probability",
        "Permutation",
        "Combination",
        "Statistics",
        "Mean",
        "Median",
        "Mode",
        "Standard deviation",
    ],
    "physics": [
        "Physics",
        "Motion",
        "Speed",
        "Velocity",
        "Acceleration",
        "Force",
        "Newton's laws of motion",
        "Momentum",
        "Inertia",
        "Friction",
        "Gravity",
        "Gravitational field",
        "Pressure",
        "Density",
        "Work (physics)",
        "Energy",
        "Kinetic energy",
        "Potential energy",
        "Power (physics)",
        "Temperature",
        "Heat",
        "Wave",
        "Frequency",
        "Wavelength",
        "Sound",
        "Reflection (physics)",
        "Refraction",
        "Diffraction",
        "Light",
        "Lens",
        "Mirror",
        "Electric charge",
        "Electric current",
        "Voltage",
        "Electrical resistance and conductance",
        "Ohm's law",
        "Electric field",
        "Magnetic field",
        "Electromagnetic induction",
        "Electromagnetic radiation",
    ],
    "chemistry": [
        "Chemistry",
        "Atom",
        "Molecule",
        "Chemical element",
        "Periodic table",
        "Chemical bond",
        "Ionic bond",
        "Covalent bond",
        "Valence electron",
        "Electron shell",
        "Isotope",
        "Ion",
        "Cation",
        "Anion",
        "Acid",
        "Base (chemistry)",
        "Salt (chemistry)",
        "pH",
        "Mole (unit)",
        "Chemical reaction",
        "Stoichiometry",
        "Oxidation state",
        "Redox",
        "Solution",
        "Solubility",
        "Concentration",
        "Chemical equilibrium",
        "Reaction rate",
        "Activation energy",
        "Catalysis",
        "Organic compound",
        "Hydrocarbon",
        "Alkane",
        "Alkene",
        "Alcohol (chemistry)",
        "Ester",
        "Polymer",
        "Endothermic process",
        "Exothermic process",
    ],
    "biology": [
        "Biology",
        "Cell (biology)",
        "Cell membrane",
        "Cytoplasm",
        "Cell nucleus",
        "Mitochondrion",
        "Chloroplast",
        "Ribosome",
        "Photosynthesis",
        "Cellular respiration",
        "Diffusion",
        "Osmosis",
        "Homeostasis",
        "DNA",
        "RNA",
        "Gene",
        "Chromosome",
        "Protein",
        "Enzyme",
        "Mitosis",
        "Meiosis",
        "Evolution",
        "Natural selection",
        "Ecology",
        "Ecosystem",
        "Food chain",
        "Food web",
        "Species",
        "Population",
        "Taxonomy (biology)",
        "Tissue (biology)",
        "Organ (biology)",
        "Organ system",
        "Nervous system",
        "Circulatory system",
        "Respiratory system",
        "Digestive system",
        "Immune system",
        "Heredity",
    ],
}

PREVIEW_LIMIT = 12


class CandidatePage(StrictModel):
    page_id: int = Field(description="Stable Wikipedia page identifier.")
    url: str = Field(description="Canonical source URL for the page.")
    title: str = Field(description="Human-readable page title.")


class DomainReport(StrictModel):
    domain: str = Field(description="Normalized STEM domain name.")
    seed_title_count: int = Field(description="Number of curated seed titles queried for the domain.")
    matched_page_count: int = Field(description="Matched page count for the domain.")
    matched_seed_titles: list[str] = Field(description="Seed titles that matched a corpus page.")
    missing_seed_titles: list[str] = Field(description="Seed titles with no exact corpus match.")
    preview_titles: list[str] = Field(description="Leading matched titles for quick inspection.")
    pages: list[CandidatePage] = Field(description="All matched pages for the domain.")


class StemReport(StrictModel):
    match_strategy: str = Field(description="Human-readable explanation of the match heuristic.")
    domain_count: int = Field(description="Number of STEM domains included.")
    total_seed_title_count: int = Field(description="Total number of seed titles across all domains.")
    total_unique_page_count: int = Field(description="Unique matched pages across all domains.")
    domains: list[DomainReport] = Field(description="Per-domain match reports.")


DomainReport.model_rebuild()
StemReport.model_rebuild()


def normalize_psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def query_domain_pages(cursor: psycopg.Cursor[tuple[object, ...]], seed_titles: list[str]) -> list[CandidatePage]:
    cursor.execute(
        """
        select page_id, url, title
        from wikipedia.documents
        where title = any(%s)
        order by title asc
        """,
        (seed_titles,),
    )
    return [
        CandidatePage(page_id=page_id, url=url, title=title)
        for page_id, url, title in cursor.fetchall()
    ]


def query_page_records(
    cursor: psycopg.Cursor[tuple[object, ...]],
    seed_titles: list[str],
) -> list[PageRecord]:
    cursor.execute(
        """
        select page_id, url, title, clean_text
        from wikipedia.documents
        where title = any(%s)
        order by title asc
        """,
        (seed_titles,),
    )
    return [
        PageRecord(page_id=page_id, url=url, title=title, clean_text=clean_text)
        for page_id, url, title, clean_text in cursor.fetchall()
    ]


def build_stem_page_records() -> list[PageRecord]:
    settings = load_settings()
    database_url = normalize_psycopg_url(settings.database_url)
    pages_by_id: dict[int, PageRecord] = {}

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for seed_titles in DOMAIN_SEED_TITLES.values():
                for page in query_page_records(cursor, seed_titles):
                    pages_by_id[page.page_id] = page

    return sorted(pages_by_id.values(), key=lambda page: page.title)


def build_domain_report(domain: str, seed_titles: list[str], pages: list[CandidatePage]) -> DomainReport:
    pages_by_title = {page.title: page for page in pages}
    matched_seed_titles = [title for title in seed_titles if title in pages_by_title]
    missing_seed_titles = [title for title in seed_titles if title not in pages_by_title]
    return DomainReport(
        domain=domain,
        seed_title_count=len(seed_titles),
        matched_page_count=len(pages),
        matched_seed_titles=matched_seed_titles,
        missing_seed_titles=missing_seed_titles,
        preview_titles=[page.title for page in pages[:PREVIEW_LIMIT]],
        pages=pages,
    )


def build_report() -> StemReport:
    settings = load_settings()
    database_url = normalize_psycopg_url(settings.database_url)
    domains: list[DomainReport] = []

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for domain, seed_titles in DOMAIN_SEED_TITLES.items():
                print(f"querying {domain}...", file=sys.stderr, flush=True)
                pages = query_domain_pages(cursor, seed_titles)
                domains.append(build_domain_report(domain, seed_titles, pages))

    unique_page_ids = {page.page_id for domain in domains for page in domain.pages}
    return StemReport(
        match_strategy="case-sensitive exact title match against curated STEM seed titles",
        domain_count=len(DOMAIN_SEED_TITLES),
        total_seed_title_count=sum(len(seed_titles) for seed_titles in DOMAIN_SEED_TITLES.values()),
        total_unique_page_count=len(unique_page_ids),
        domains=domains,
    )


def main() -> None:
    report = build_report()
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()
