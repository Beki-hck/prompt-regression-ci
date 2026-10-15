"""Beki's feature: flaky case detection. Remove the skip once gate.flaky_cases is written."""
import pytest

from promptci.gate import flaky_cases


@pytest.mark.skip(reason="Beki writes gate.flaky_cases without AI")
def test_flaky_cases():
    run = {"cases": [{"id": "a", "pass_rate": 1.0}, {"id": "b", "pass_rate": 0.67},
                     {"id": "c", "pass_rate": 0.0}, {"id": "d", "pass_rate": 0.33}]}
    assert flaky_cases(run) == ["b", "d"]
    assert flaky_cases({"cases": []}) == []
