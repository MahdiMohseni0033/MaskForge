from pathlib import Path

import pytest

from sam3_app.models import ModelConfigurationError, SAM3Paths


def test_paths_require_official_source(tmp_path: Path) -> None:
    with pytest.raises(ModelConfigurationError, match="Official SAM 3 source"):
        SAM3Paths(tmp_path).validate()
