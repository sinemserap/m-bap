"""Smoke test – verifies the pipeline module can be imported."""

import importlib


def test_import():
    assert importlib.import_module("code.pipeline") is not None
