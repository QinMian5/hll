"""
Abstract: Shared card-quality standard for source-pipeline card tasks.
Out of scope: Queue transport behavior and worker protocol instructions.
"""

from __future__ import annotations

CARD_QUALITY_STANDARD = (
    "Each card represents one knowledge unit.\n\n"
    "The title must follow Title Case style and must not include qualifiers beyond what "
    "is needed for minimal disambiguation. If the same term could reasonably refer to "
    "different meanings across domains, add a parenthesized domain qualifier for "
    "disambiguation: <Subject> (<Domain>).\n\n"
    "The title should be self-descriptive, allowing readers to infer the main topic "
    "without reading the content. Each card should maintain a one-to-one mapping between "
    "title and content, ensuring topical coherence.\n\n"
    "Given standard domain terminology, the content must be focused, compact, "
    "self-contained, and self-explanatory. It must not contain hidden assumptions, "
    "external prerequisites, missing context, hidden dependencies, or unresolved "
    "references.\n\n"
    "Definitions, qualifiers, mechanisms, examples, or implications may stay together "
    "when they help readers understand the same knowledge unit.\n\n"
    "Content LaTeX validity:\n"
    "If the content contains LaTeX math, inline math must use \\( and \\), display math "
    "must use \\[ and \\], and malformed LaTeX or $ / $$ delimiters are not allowed."
)


def build_quality_criteria_instruction_text() -> str:
    return f"Card quality standard:\n{CARD_QUALITY_STANDARD}"
