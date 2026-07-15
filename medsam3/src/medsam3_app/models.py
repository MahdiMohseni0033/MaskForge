"""Safe integration boundary for the official MedSAM3 repository."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Iterator, Literal


class ModelConfigurationError(RuntimeError):
    """Raised with an actionable message when MedSAM3 is not installed."""


DeviceChoice = Literal["auto", "cpu", "cuda"]


@dataclass(frozen=True)
class MedSAM3Paths:
    """Locations required by the upstream MedSAM3 inference implementation."""

    repository: Path
    config: Path
    weights: Path

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "MedSAM3Paths":
        root = project_root or Path(__file__).resolve().parents[2]
        repository = Path(os.environ.get("MEDSAM3_REPO_DIR", root / "third_party" / "MedSAM3"))
        config = Path(os.environ.get("MEDSAM3_CONFIG", repository / "configs" / "full_lora_config.yaml"))
        weights = Path(
            os.environ.get(
                "MEDSAM3_LORA_WEIGHTS",
                repository / "outputs" / "sam3_lora_full" / "best_lora_weights.pt",
            )
        )
        return cls(repository=repository, config=config, weights=weights)

    def validate(self) -> None:
        required = {
            "MedSAM3 inference script": self.repository / "infer_sam.py",
            "MedSAM3 configuration": self.config,
            "MedSAM3 LoRA weights": self.weights,
        }
        missing = [f"{label}: {path}" for label, path in required.items() if not path.is_file()]
        if not self.repository.is_dir():
            missing.insert(0, f"MedSAM3 repository: {self.repository}")
        if missing:
            joined = "\n".join(f"• {item}" for item in missing)
            raise ModelConfigurationError(
                "MedSAM3 is not ready. Run the setup commands in README.md, then confirm:\n" + joined
            )


def resolve_device(choice: DeviceChoice) -> str:
    """Resolve the requested device without requiring torch at module-import time."""
    if choice == "cpu":
        return "cpu"
    try:
        import torch
    except ImportError as error:
        raise ModelConfigurationError("PyTorch is missing. Run scripts/bootstrap_medsam3.py first.") from error

    cuda_available = torch.cuda.is_available()
    if choice == "cuda" and not cuda_available:
        raise ModelConfigurationError("CUDA was selected but PyTorch cannot access a CUDA device.")
    return "cuda" if cuda_available and choice in {"auto", "cuda"} else "cpu"


def load_medsam3_model(
    paths: MedSAM3Paths,
    *,
    device: DeviceChoice = "auto",
    threshold: float = 0.5,
    nms_iou: float = 0.5,
    resolution: int = 1008,
):
    """Load the official upstream SAM3+LoRA inferencer in evaluation mode."""
    paths.validate()
    selected_device = resolve_device(device)
    module = _load_upstream_module(paths.repository)
    with _working_directory(paths.repository):
        return module.SAM3LoRAInference(
            config_path=str(paths.config),
            weights_path=str(paths.weights),
            resolution=resolution,
            detection_threshold=threshold,
            nms_iou_threshold=nms_iou,
            device=selected_device,
        )


def create_box_processor(inferencer, *, resolution: int, threshold: float):
    """Create the official SAM 3 image processor around the LoRA-adapted model."""
    try:
        from sam3.model.sam3_image_processor import Sam3Processor
    except ImportError as error:
        raise ModelConfigurationError(f"Could not import the SAM 3 box-prompt processor: {error}") from error
    return Sam3Processor(
        inferencer.model,
        resolution=resolution,
        device=inferencer.device,
        confidence_threshold=threshold,
    )


def upstream_working_directory(paths: MedSAM3Paths) -> Iterator[None]:
    """Expose the upstream working-directory context for prediction calls."""
    return _working_directory(paths.repository)


def _load_upstream_module(repository: Path) -> ModuleType:
    module_name = "_medsam3_upstream_infer_sam"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    script = repository / "infer_sam.py"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise ModelConfigurationError(f"Could not import the upstream script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(repository))
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ModelConfigurationError(f"Could not import MedSAM3 dependencies: {error}") from error
    finally:
        if sys.path and sys.path[0] == str(repository):
            sys.path.pop(0)
    sys.modules[module_name] = module
    return module


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
