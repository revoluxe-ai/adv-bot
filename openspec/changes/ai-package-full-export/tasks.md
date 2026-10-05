## 1. Domain gaps + assembler

- [x] 1.1 Add `PACKAGE_FAMILY_GAPS.json` builder and dataset card (`family_gaps.py`)
- [x] 1.2 Add `DatasetId.PACKAGE_FAMILY_GAPS` enum
- [x] 1.3 Implement `PackageZipAssembler` (`package_zip_assembler.py`)
- [x] 1.4 Extend validator for gaps payload semantics

## 2. Operator CLI

- [x] 2.1 Add `scripts/ai_package_v1_export.py` (one shop, period, output path)

## 3. Tests

- [x] 3.1 Unit tests: assembler ZIP + gaps + deterministic hash
- [x] 3.2 Unit test: CLI import boundary (no WB)

## 4. Verify

- [x] 4.1 `pytest -m unit tests/unit/ai_package_v1/`
- [x] 4.2 `poetry run pyright-strict` on touched modules
