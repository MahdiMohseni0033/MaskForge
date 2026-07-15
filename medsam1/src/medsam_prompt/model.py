"""Model loading for the official bowang-lab MedSAM source tree."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys


class ModelConfigurationError(RuntimeError):
    """Raised when an actionable MedSAM resource is missing."""


@dataclass(frozen=True)
class MedSAMPaths:
    repository: Path
    checkpoint: Path

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "MedSAMPaths":
        root = project_root or Path(__file__).resolve().parents[2]
        repository = Path(os.environ.get("MEDSAM_REPO_DIR", root / "third_party" / "MedSAM"))
        checkpoint = Path(os.environ.get("MEDSAM_CHECKPOINT", root / "checkpoints" / "medsam_vit_b.pth"))
        return cls(repository=repository, checkpoint=checkpoint)

    def validate(self) -> None:
        missing: list[str] = []
        if not (self.repository / "segment_anything").is_dir():
            missing.append(f"MedSAM source: {self.repository}")
        if not self.checkpoint.is_file():
            missing.append(f"MedSAM checkpoint: {self.checkpoint}")
        if missing:
            details = "\n".join(f"• {item}" for item in missing)
            raise ModelConfigurationError(
                "MedSAM is not ready. Run the setup commands in README.md, then confirm:\n" + details
            )


def select_device(choice: str = "auto") -> str:
    try:
        import torch
    except ImportError as error:
        raise ModelConfigurationError("PyTorch is missing. Install the environment dependencies first.") from error
    if choice == "cpu":
        return "cpu"
    if choice == "cuda" and not torch.cuda.is_available():
        raise ModelConfigurationError("CUDA was selected but PyTorch cannot access a GPU.")
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_medsam(paths: MedSAMPaths, device_choice: str = "auto"):
    """Load the official MedSAM ViT-B checkpoint in evaluation mode."""
    paths.validate()
    device = select_device(device_choice)
    repository = str(paths.repository)
    if repository not in sys.path:
        sys.path.insert(0, repository)
    try:
        from segment_anything import sam_model_registry
    except ImportError as error:
        raise ModelConfigurationError(
            "Could not import the official MedSAM package. Run `pip install -e third_party/MedSAM --no-deps`."
        ) from error
    model = sam_model_registry["vit_b"](checkpoint=str(paths.checkpoint))
    return model.to(device).eval(), device
