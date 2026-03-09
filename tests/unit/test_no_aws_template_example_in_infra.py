"""Assert AWSTemplateExampleGeneratorAdapter lives in providers/aws, not infrastructure."""

import importlib
from pathlib import Path


def test_old_path_does_not_exist():
    old_path = Path(
        "src/orb/infrastructure/adapters/template_example_generator_adapter.py"
    )
    assert not old_path.exists(), (
        f"{old_path} still exists — move it to "
        "src/orb/providers/aws/adapters/template_example_generator_adapter.py"
    )


def test_new_path_exists():
    new_path = Path(
        "src/orb/providers/aws/adapters/template_example_generator_adapter.py"
    )
    assert new_path.exists(), (
        f"{new_path} does not exist — "
        "move AWSTemplateExampleGeneratorAdapter there"
    )


def test_new_path_is_importable():
    mod = importlib.import_module(
        "orb.providers.aws.adapters.template_example_generator_adapter"
    )
    assert hasattr(mod, "AWSTemplateExampleGeneratorAdapter")
