#!/usr/bin/env python3
"""
Abstract: Import the authoritative LCC taxonomy tree into the local API database.
Out of scope: Incremental taxonomy updates and assignment workflow orchestration.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from entrypoints.runtime import get_runtime_dependencies
from modules.taxonomy.importer import TaxonomyImporter
from modules.taxonomy.repo import TaxonomyRepo

_ROOT_DIR = Path(__file__).resolve().parents[1]
_LCC_PATH = _ROOT_DIR / "apps" / "operator_tools" / "assets" / "taxonomy" / "lcc.yaml"


async def _main() -> None:
    runtime = get_runtime_dependencies()
    async with runtime.session_factory() as session:
        importer = TaxonomyImporter(repo=TaxonomyRepo(session=session))
        imported_count = await importer.import_yaml_file(_LCC_PATH)
        print(f"taxonomy import completed rows={imported_count}")


if __name__ == "__main__":
    asyncio.run(_main())
