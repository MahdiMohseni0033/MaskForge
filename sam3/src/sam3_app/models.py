"""Integration boundary for the official facebookresearch/sam3 repository."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any, Literal


class ModelConfigurationError(RuntimeError):
    """Raised with an actionable message when official SAM 3 is unavailable."""


DeviceChoice = Literal["auto", "cpu", "cuda"]


@dataclass(frozen=True)
class SAM3Paths:
    repository: Path
    checkpoint: Path | None = None

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "SAM3Paths":
        root = project_root or Path(__file__).resolve().parents[2]
        repository = Path(os.environ.get("SAM3_REPO_DIR", root / "third_party" / "sam3"))
        checkpoint_value = os.environ.get("SAM3_CHECKPOINT")
        checkpoint = Path(checkpoint_value).expanduser() if checkpoint_value else None
        return cls(repository=repository, checkpoint=checkpoint)

    def validate(self) -> None:
        missing: list[str] = []
        if not (self.repository / "sam3" / "model_builder.py").is_file():
            missing.append(f"Official SAM 3 source: {self.repository}")
        if self.checkpoint is not None and not self.checkpoint.is_file():
            missing.append(f"SAM 3 checkpoint: {self.checkpoint}")
        if missing:
            details = "\n".join(f"• {item}" for item in missing)
            raise ModelConfigurationError(
                "SAM 3 is not ready. Run the setup commands in README.md, then confirm:\n" + details
            )


@dataclass(frozen=True)
class LoadedSAM3:
    model: Any
    device: str


def resolve_device(choice: DeviceChoice) -> str:
    try:
        import torch
    except ImportError as error:
        raise ModelConfigurationError("PyTorch is missing. Complete the README setup first.") from error

    if choice == "cpu":
        return "cpu"
    if choice == "cuda" and not torch.cuda.is_available():
        raise ModelConfigurationError("CUDA was selected but PyTorch cannot access a CUDA device.")
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_sam3_model(paths: SAM3Paths, device: DeviceChoice = "auto") -> LoadedSAM3:
    """Load official SAM 3 with its native instance-interactive image predictor."""
    paths.validate()
    selected_device = resolve_device(device)
    repository = str(paths.repository)
    if repository not in sys.path:
        sys.path.insert(0, repository)
    try:
        from sam3 import build_sam3_image_model
    except ImportError as error:
        raise ModelConfigurationError(
            "Could not import official SAM 3. Run scripts/bootstrap_sam3.py in this environment."
        ) from error

    try:
        model = build_sam3_image_model(
            device=selected_device,
            checkpoint_path=str(paths.checkpoint) if paths.checkpoint else None,
            load_from_HF=paths.checkpoint is None,
            enable_inst_interactivity=True,
        )
    except Exception as error:
        raise ModelConfigurationError(f"Could not load the official SAM 3 model: {error}") from error
    return LoadedSAM3(model=model.eval(), device=selected_device)


def create_processor(loaded: LoadedSAM3):
    try:
        from sam3.model.sam3_image_processor import Sam3Processor
    except ImportError as error:
        raise ModelConfigurationError(f"Could not import the SAM 3 image processor: {error}") from error
    return Sam3Processor(loaded.model, resolution=1008, device=loaded.device)
