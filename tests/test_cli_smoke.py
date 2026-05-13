import subprocess
import sys


def test_import_and_help():
    result = subprocess.run(
        [sys.executable, "-m", "polyforge", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "validate" in result.stdout
    assert "export" in result.stdout
    assert "featurize" in result.stdout
    assert "train" in result.stdout
