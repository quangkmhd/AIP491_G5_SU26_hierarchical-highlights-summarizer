"""
Audio Utilities
"""
import numpy as np
import torchaudio
import torch


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    """Resample audio numpy 1D từ orig_sr sang target_sr."""
    if orig_sr == target_sr:
        return audio
    tensor = torch.from_numpy(audio).float().unsqueeze(0)
    resampled = torchaudio.functional.resample(tensor, orig_freq=orig_sr, new_freq=target_sr)
    return resampled.squeeze(0).numpy()


def chunk_audio(audio: np.ndarray, sample_rate: int, chunk_length_s: float = 2.5, overlap_s: float = 0.3) -> list[np.ndarray]:
    """
    Cắt audio thành các chunk có độ dài cố định, có overlap.
    Trả về danh sách numpy arrays.
    """
    chunk_size = int(sample_rate * chunk_length_s)
    overlap_size = int(sample_rate * overlap_s)
    stride = chunk_size - overlap_size

    chunks = []
    for start in range(0, len(audio), stride):
        end = start + chunk_size
        chunk = audio[start:end]
        # Pad chunk cuối nếu ngắn hơn chunk_size
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
        chunks.append(chunk)

    return chunks


def load_audio_file(file_path: str, target_sr: int = 16000) -> np.ndarray:
    """Load file audio, tự động resample và convert mono."""
    waveform, sr = torchaudio.load(file_path)

    # Convert stereo → mono
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # Resample nếu cần
    if sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, orig_freq=sr, new_freq=target_sr)

    return waveform.squeeze(0).numpy()
