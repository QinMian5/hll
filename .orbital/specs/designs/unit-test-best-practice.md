---
abstract: Standalone unit-test handbook for behavior-focused, deterministic, and maintainable software verification.
out_of_scope: Project-specific architecture maps, CI vendor pipeline wiring, and framework-specific integration harness details.

---

# Unit Test Standards and Playbook

## Module Responsibility

This document defines a standalone, practice-ready standard for writing and reviewing unit tests.
It owns:

1. Unit-test purpose and quality criteria.
2. Unit boundary definitions and marker placement rules.
3. Mandatory and forbidden test-content categories.
4. Behavior-change policy for test evolution.
5. Practical writing patterns with positive and negative examples.
6. Review checklist used for implementation and code review.
7. Onboarding exercises for training new engineers.

This document does not own project-specific architecture decisions, integration test orchestration details, or CI platform setup.

## How To Use This Handbook

1. Use this document as the default standard when writing new unit tests.
2. Use the checklist section during code review for test quality gating.
3. Use the scenario examples for onboarding and pair-programming training.
4. Adapt naming and marker conventions to local repository conventions without changing the core principles.

## Canonical Unit-Test Objective

Unit tests SHALL act as executable specifications for current accepted behavior.

1. Unit tests SHALL validate functional and domain behavior, not repository layout constraints.
2. Unit tests SHALL provide fast and deterministic feedback suitable for frequent local runs and CI gates.
3. Unit tests SHALL protect against regressions by codifying accepted behavior and invariants.
4. Unit tests SHALL remain resilient to internal refactoring when public behavior is unchanged.
5. Unit tests SHALL prioritize readability and newcomer comprehension over excessive abstraction.

## Current-Truth And Behavior-Change Policy

This handbook uses current-truth testing semantics.

1. Tests SHALL specify current accepted behavior only.
2. When behavior changes from `A` to `B`, unit tests SHALL be updated to specify `B`.
3. Tests that enforce superseded behavior SHALL be removed or rewritten in the same change set that updates behavior.
4. Historical behavior notes SHALL live in changelog/ADR material, not in active unit-test assertions.
5. A legacy behavior assertion MAY remain only if backward compatibility is an active requirement.
6. If compatibility is required, tests SHALL express compatibility as a current contract, not as historical commentary.

## Unit Boundary Definition

A test belongs to the `unit` layer when it validates one cohesive behavior with controlled dependencies and deterministic outcomes.

### In Scope For Unit Tests

1. Pure functions and deterministic domain transformations.
2. Schema validation and normalization behavior (accepted input forms, rejected forms, error semantics).
3. Rule-level orchestration that can run with in-memory fakes/stubs.
4. Error-path behavior where the unit translates or propagates exceptions by contract.
5. Deterministic algorithmic stages with bounded input/output contracts.
6. Small adapter behavior that can be verified with isolated stubs.

### Out Of Scope For Unit Tests

1. Real network calls, real external services, or remote file systems.
2. Full workflow execution through real process orchestration.
3. Cross-process integration behavior that depends on external runtime state.
4. Repository structural checks (for example directory names) unrelated to behavior contracts.
5. Performance benchmarking and throughput claims.

## Layer And Marker Contract

This handbook defines generic marker intent. Actual marker names MAY vary by repository.

1. `unit` SHALL represent deterministic, isolated tests with controlled collaborators.
2. `integration` SHALL represent tests crossing filesystem/process/service boundaries.
3. `slow` SHALL represent tests with runtime unsuitable for fast feedback loops.
4. `e2e` SHALL represent user-flow or full-stack contract verification.
5. A test SHALL NOT be classified as `unit` if it requires uncontrolled external mutable state.

## Unit Test Selection Matrix

Use this decision matrix when selecting what to test:

1. If behavior has user/business impact and is deterministic, add a unit test.
2. If behavior is pure formatting/parsing/validation logic, add unit tests first.
3. If behavior requires real infrastructure to be meaningful, prefer integration tests.
4. If behavior already has strong lower-layer coverage, avoid duplicate high-layer assertions.
5. If a bug escaped to production, add the narrowest deterministic regression test that reproduces it.

## Determinism And Isolation Rules

1. Unit tests SHALL be deterministic across repeated runs on unchanged code.
2. Unit tests SHALL isolate mutable state per test case.
3. Unit tests SHALL NOT depend on test execution order.
4. Randomness SHALL be controlled through seeded interfaces or injected generators.
5. Time-dependent behavior SHALL be controlled through injected time providers.
6. Environment-variable dependencies SHALL be isolated with fixture-controlled setup and teardown.
7. Temporary filesystem usage SHALL use test-owned temporary paths.
8. Global process state changes SHALL be reverted in fixture finalization.
9. Unit tests SHOULD avoid dependence on locale/timezone defaults unless those defaults are the behavior under test.

## Fixture And Test-Data Governance

1. Shared, business-agnostic fixtures SHOULD be centralized in a common fixture module (for example `tests/conftest.py`).
2. Feature-local fixtures SHOULD stay near local test modules when sharing scope is local.
3. File-based test inputs SHOULD be test-owned under a dedicated test-data directory (for example `tests/data/`).
4. Unit tests SHALL NOT read runtime production configuration files directly.
5. Fixture interfaces SHALL be stable, explicit, and named by behavior role.
6. Fixtures SHALL avoid hidden global side effects.
7. Autouse fixtures SHALL be used only when they represent universal test preconditions.

## Mandatory Unit-Test Content

The following categories are mandatory when relevant to changed behavior.

1. Nominal-path behavior for each externally callable unit contract.
2. Boundary and edge input behavior.
3. Validation failure semantics and error types/messages where contractually relevant.
4. Domain invariants and conservation rules.
5. Deterministic ordering/selection semantics where output ranking matters.
6. Regression cases for fixed defects.
7. Serialization/deserialization normalization behavior for schema-level units.
8. Exception propagation or translation behavior at explicit boundaries.
9. Contract-level defaults and fallback behavior.
10. Stability expectations for ordering, tie-breaking, and deterministic selection.

## Forbidden Unit-Test Content

The following categories SHALL NOT be used as primary unit-test targets.

1. Private method existence or direct private-method testing.
2. Internal call sequence assertions that do not represent observable behavior.
3. Assertions on incidental implementation details such as temporary variable names.
4. Duplicated coverage of the same condition across multiple layers without additional confidence value.
5. Assertions against third-party library internals outside repository-owned contracts.
6. Brittle snapshot-style assertions over large opaque payloads when focused assertions can express the contract.
7. Use of `sleep` for timing-sensitive synchronization in unit tests.
8. Permanent quarantine by non-strict `xfail` without active follow-up ownership.
9. Assertions that lock obsolete behavior after approved behavior changes.
10. Large end-to-end setup hidden inside so-called unit tests.

## Unit-Test Writing Workflow

The default workflow for each behavior addition or change:

1. Identify the behavior contract in design and code boundaries.
2. Write or update unit tests that describe the intended current behavior.
3. Ensure tests fail for incorrect behavior before implementation is complete.
4. Implement or modify production code to satisfy behavior.
5. Refactor tests for readability while preserving behavior intent.
6. Recheck marker, fixture, and determinism compliance.
7. Remove or rewrite superseded behavior tests in the same change set.

## TDD Alignment Guidance

TDD is compatible with selective and valuable testing.

1. Red step SHALL target behavior, not implementation internals.
2. Green step SHOULD implement only what is needed for the behavior under test.
3. Refactor step SHALL preserve behavior tests while improving code structure.
4. Not every line requires a unit test; every critical behavior contract does.
5. Deleting obsolete tests during behavior changes is a valid and required maintenance action.

## Assertion Strategy

1. Assertions SHALL target outcomes visible at the tested contract boundary.
2. Each test SHOULD focus on one behavior condition.
3. Parametrization SHOULD be used when one behavior is repeated across structured input classes.
4. Assertion messages SHOULD communicate business meaning when failure context is ambiguous.
5. Floating-point assertions SHOULD use tolerant comparisons when mathematically appropriate.
6. Error assertions SHOULD verify both exception class and critical semantic content when contractually required.
7. One test SHOULD focus on one behavior claim, even if setup is shared.
8. Broad `assert result == huge_payload` SHOULD be replaced by focused semantic assertions.

## Test Naming And Structure

1. Test names SHALL encode behavior intent and expected outcome.
2. Tests SHALL use clear Arrange/Act/Assert flow.
3. Shared setup SHALL be extracted into fixtures when repetition harms readability.
4. Tests SHALL remain explicit enough that a newcomer can infer behavior without reading implementation first.
5. Generic names such as `test_case_1` or `test_smoke` SHALL NOT be used.
6. Tests SHOULD avoid internal branching (`if/for/switch`) unless the branching is the behavior under test.

## Common Scenarios With Positive And Negative Examples

### Scenario 1: Pure Function Behavior

Positive:

```python
import pytest

from app.domain.math import clamp


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,lower,upper,expected",
    [
        (1.0, 0.0, 2.0, 1.0),
        (-1.0, 0.0, 2.0, 0.0),
        (3.0, 0.0, 2.0, 2.0),
    ],
)
def test_clamp_returns_value_within_bounds(value, lower, upper, expected):
    result = clamp(value=value, lower=lower, upper=upper)
    assert result == expected
```

Negative:

```python
import pytest

from app.domain import math


@pytest.mark.unit
def test_clamp_uses_internal_temp_variable_name():
    assert "tmp_val" in math.clamp.__code__.co_varnames
```

Reason: internal variable names are not behavior contracts.

### Scenario 2: Schema Validation And Error Semantics

Positive:

```python
import pytest
from pydantic import ValidationError

from app.schemas.quantity import LengthQuantity


@pytest.mark.unit
def test_length_quantity_rejects_non_length_units():
    with pytest.raises(ValidationError) as excinfo:
        LengthQuantity(value=3.0, unit="kelvin")
    assert "dimensionality" in str(excinfo.value).lower()
```

Negative:

```python
import pytest

from app.schemas import quantity


@pytest.mark.unit
def test_length_quantity_calls_parse_units_once(mocker):
    spy = mocker.spy(quantity.ureg, "parse_units")
    quantity.LengthQuantity(value=3.0, unit="nm")
    assert spy.call_count == 1
```

Reason: call-count verification of implementation internals is brittle unless explicit performance contract exists.

### Scenario 3: Behavior Change From Legacy A To Current B

Current accepted behavior:

```python
import pytest

from app.domain.thresholds import normalize_threshold


@pytest.mark.unit
def test_normalize_threshold_uses_dimensionless_default_when_unit_missing():
    value = normalize_threshold("0.20")
    assert value.value == 0.20
    assert value.unit == "dimensionless"
```

Forbidden stale assertion:

```python
import pytest

from app.domain.thresholds import normalize_threshold


@pytest.mark.unit
def test_normalize_threshold_rejects_unitless_values():
    with pytest.raises(ValueError):
        normalize_threshold("0.20")
```

Reason: stale tests that enforce superseded behavior must be removed when behavior contract changes.

### Scenario 4: Time-Dependent Logic

Positive:

```python
import datetime as dt
import pytest

from app.domain.window import WindowPolicy


class FixedClock:
    def __init__(self, now: dt.datetime) -> None:
        self._now = now

    def now(self) -> dt.datetime:
        return self._now


@pytest.mark.unit
def test_window_policy_blocks_expired_items():
    clock = FixedClock(dt.datetime(2026, 3, 23, 12, 0, 0))
    policy = WindowPolicy(clock=clock)
    assert policy.is_allowed(expire_at=dt.datetime(2026, 3, 23, 11, 59, 59)) is False
```

Negative:

```python
import datetime as dt
import pytest
import time

from app.domain.window import WindowPolicy


@pytest.mark.unit
def test_window_policy_blocks_expired_items():
    policy = WindowPolicy()
    time.sleep(1)
    assert policy.is_allowed(expire_at=dt.datetime.utcnow()) is False
```

Reason: real clock and sleep-based timing cause non-determinism and flakiness.

### Scenario 5: Randomized Behavior

Positive:

```python
import random
import pytest

from app.domain.sampling import choose_candidates


@pytest.mark.unit
def test_choose_candidates_is_reproducible_with_seed():
    rng = random.Random(7)
    first = choose_candidates(pool=list(range(10)), k=4, rng=rng)
    rng = random.Random(7)
    second = choose_candidates(pool=list(range(10)), k=4, rng=rng)
    assert first == second
```

Negative:

```python
import pytest

from app.domain.sampling import choose_candidates


@pytest.mark.unit
def test_choose_candidates_contains_expected_item():
    result = choose_candidates(pool=list(range(10)), k=4)
    assert 3 in result
```

Reason: uncontrolled randomness leads to intermittent failures.

### Scenario 6: File IO Boundaries

Positive unit test for parser logic:

```python
import pytest

from app.io.parsers import parse_discount_text


@pytest.mark.unit
def test_parse_discount_text_parses_numeric_token():
    parsed = parse_discount_text("discount = 0.15")
    assert parsed.value == 0.15
```

Negative unit test mixing real filesystem integration:

```python
import pytest

from app.io.config_reader import read_config


@pytest.mark.unit
def test_read_config_reads_real_file():
    cfg = read_config("/etc/company/default.yaml")
    assert cfg is not None
```

Reason: real external filesystem and environment configuration belong to integration testing.

### Scenario 7: Exception Contracts

Positive:

```python
import pytest

from app.domain.validation import InvalidOrderError
from app.domain.validation import validate_order


@pytest.mark.unit
def test_validate_order_raises_invalid_order_error_for_invalid_state():
    with pytest.raises(InvalidOrderError) as excinfo:
        validate_order(order={"status": "archived", "amount": -1})
    assert "amount" in str(excinfo.value).lower()
```

Negative:

```python
import pytest

from app.domain import validation


@pytest.mark.unit
def test_validate_order_wraps_error_with_custom_message_exactly():
    with pytest.raises(RuntimeError, match="WrappedError: invalid"):
        validation.validate_order(order={"status": "archived", "amount": -1})
```

Reason: tests should not enforce unnecessary wrapper behavior when wrapper semantics are not a contract.

### Scenario 8: Parametrization For Rule Families

Positive:

```python
import pytest

from app.domain.currency import convert_amount


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,target,expected",
    [
        ((100.0, "USD"), "EUR", 90.0),
        ((100.0, "EUR"), "USD", 111.11),
    ],
)
def test_convert_amount_converts_currency(value, target, expected):
    amount, source = value
    result = convert_amount(amount=amount, source_currency=source, target_currency=target)
    assert result == pytest.approx(expected, rel=1e-2)
```

Negative:

```python
import pytest

from app.domain.currency import convert_amount


@pytest.mark.unit
def test_convert_amount_many_cases_with_logic():
    cases = [(100.0, "USD", "EUR", 90.0), (100.0, "EUR", "USD", 111.11)]
    expected = [90.0, 111.11]
    for idx, case in enumerate(cases):
        amount, src, target, _ = case
        result = convert_amount(amount=amount, source_currency=src, target_currency=target)
        assert result == expected[idx]
```

Reason: loop-index assertion logic obscures failing case identity and reduces readability.

### Scenario 9: Shared Fixture Placement

Positive (`tests/conftest.py`):

```python
import pytest


@pytest.fixture
def sample_order_payload():
    return {"status": "pending", "amount": 120.0, "currency": "USD"}
```

Positive (test file):

```python
import pytest

from app.domain.validation import validate_order


@pytest.mark.unit
def test_validate_order_accepts_shared_fixture_payload(sample_order_payload):
    validated = validate_order(order=sample_order_payload)
    assert validated["status"] == "pending"
```

Negative:

```python
import pytest


@pytest.mark.unit
def test_validate_order_accepts_payload():
    payload = {"status": "pending", "amount": 120.0, "currency": "USD"}
    # dozens of near-identical payload copies appear in many files
```

Reason: stable shared setup should be centralized.

### Scenario 10: Regression Test For Fixed Defect

Positive:

```python
import pytest

from app.domain.ranking import choose_best_offer


@pytest.mark.unit
def test_choose_best_offer_prefers_highest_score_when_counts_tie():
    offers = [
        {"match_count": 10, "score": 0.70},
        {"match_count": 10, "score": 0.75},
    ]
    winner = choose_best_offer(offers)
    assert winner["score"] == 0.75
```

Negative:

```python
import pytest

from app.domain.ranking import choose_best_offer


@pytest.mark.unit
def test_choose_best_offer_case_1():
    # unclear intent and no bug linkage
    winner = choose_best_offer([{"match_count": 10, "score": 0.70}])
    assert winner is not None
```

Reason: regression tests should preserve explicit defect-relevant behavior.

### Scenario 11: Interaction Contract Without Over-Mocking

Positive:

```python
import pytest

from app.domain.checkout import build_receipt


class FakeTaxService:
    def calculate(self, subtotal):
        return subtotal * 0.1


@pytest.mark.unit
def test_build_receipt_returns_total_with_tax():
    receipt = build_receipt(subtotal=100.0, tax_service=FakeTaxService())
    assert receipt["subtotal"] == 100.0
    assert receipt["tax"] == pytest.approx(10.0)
    assert receipt["total"] == pytest.approx(110.0)
```

Negative:

```python
import pytest

from app.domain.checkout import build_receipt


@pytest.mark.unit
def test_build_receipt_calls_tax_service_exactly_once(mocker):
    tax_service = mocker.Mock()
    tax_service.calculate.return_value = 10.0
    build_receipt(subtotal=100.0, tax_service=tax_service)
    tax_service.calculate.assert_called_once_with(100.0)
```

Reason: behavior-focused output assertions are usually more resilient than strict call choreography assertions.

## Anti-Pattern Catalog

The following anti-patterns SHALL be treated as review defects.

1. Assertion against private methods.
2. Test names without behavior semantics (`test_case_1`, `test_smoke`).
3. Hidden dependence on system clock, random seed, locale, or environment.
4. Multi-behavior mega-tests that obscure failure diagnosis.
5. Conditional logic inside test body that duplicates production branching.
6. Fixture factories that hide critical setup details and reduce readability.
7. Broad mocks that validate call choreography instead of behavior.
8. Unowned `xfail` marks without issue reference and expiration intent.
9. Golden snapshots used as a substitute for semantic assertions in unit scope.
10. Unit tests that silently pass due to missing assertions.

## Unit Test Review Checklist

Each new or modified unit test SHALL satisfy this checklist:

1. The test validates current accepted behavior.
2. The test is deterministic and order-independent.
3. The test marker classification is correct (`unit` vs others).
4. The assertions target behavior, not incidental implementation details.
5. Shared setup is managed by fixtures where appropriate.
6. Test data ownership follows `tests/data/**` and fixture injection rules.
7. No stale assertions preserve superseded behavior.
8. Failure messages and naming make intent obvious.
9. The test provides unique confidence and is not redundant with higher layers.
10. Runtime profile is suitable for frequent checks unless explicitly marked otherwise.
11. The test would still be valid after internal refactoring that preserves behavior.
12. If behavior changed, stale tests have been removed or rewritten.

## Onboarding Exercise Set For New Contributors

This section defines a generic onboarding progression for writing high-quality unit tests.

1. Write one nominal-path and one edge-path unit test for a pure domain function.
2. Write one schema-validation test that verifies accepted and rejected inputs.
3. Convert one duplicated local setup block into a shared fixture.
4. Rewrite one brittle implementation-detail assertion into a behavior assertion.
5. Add one regression test for a realistic defect scenario.
6. Perform self-review against the checklist and document pass/fail status.

## Quick Adoption Plan

Teams adopting this handbook SHOULD execute these steps:

1. Align marker names and test folder conventions with local standards.
2. Add the review checklist to pull-request templates.
3. Refactor one existing brittle test file using the scenario guidance.
4. Run onboarding exercises for each new team member.
5. Review and tune this handbook quarterly based on defect escape data.