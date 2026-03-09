"""TDD test: config_builder.py belongs in providers/aws/, not providers/."""
import importlib
import os


def test_old_config_builder_does_not_exist():
    old_path = os.path.join(
        os.path.dirname(__file__),
        "../../src/orb/providers/config_builder.py",
    )
    assert not os.path.exists(os.path.normpath(old_path)), (
        "src/orb/providers/config_builder.py should have been moved to "
        "src/orb/providers/aws/config_builder.py"
    )


def test_new_config_builder_exists_and_is_importable():
    new_path = os.path.join(
        os.path.dirname(__file__),
        "../../src/orb/providers/aws/config_builder.py",
    )
    assert os.path.exists(os.path.normpath(new_path)), (
        "src/orb/providers/aws/config_builder.py does not exist"
    )
    module = importlib.import_module("orb.providers.aws.config_builder")
    assert module is not None
