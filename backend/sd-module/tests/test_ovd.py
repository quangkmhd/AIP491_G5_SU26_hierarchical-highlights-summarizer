from pathlib import Path

import numpy as np

from core.ovd import PyannoteOVD


def test_missing_optional_checkpoint_disables_overlap_detection(tmp_path: Path) -> None:
    ovd = PyannoteOVD(
        {
            "audio": {"sample_rate": 16000},
            "model_paths": {"pyannote_segmentation": str(tmp_path / "missing.bin")},
        }
    )

    assert ovd.detect_overlap(np.zeros(16000, dtype=np.float32)) is False
    assert ovd.audio_buffer.size == 0
