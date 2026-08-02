import logging
import os
import sys

import segeval
import numpy as np
from sklearn.metrics import f1_score

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data import Corpus, EvalLoader  # noqa: E402
from src.service.sliding_text_tiling import SlidingTextTilingService  # noqa: E402
from src.config.text_tiling import SlidingTextTilingConfig  # noqa: E402

logging.disable(logging.CRITICAL)

def boundaries_to_binary(boundary_indices, total_entries):
    binary_list = [0] * total_entries
    for index in boundary_indices:
        if 0 <= index < total_entries:
            binary_list[index] = 1
    binary_list[-1] = 1
    return binary_list

def segments_to_binary(segment_sizes):
    total_length = sum(segment_sizes)
    binary_list = [0] * total_length
    end_indices = [sum(segment_sizes[:i+1]) for i in range(len(segment_sizes))]
    for index in end_indices[:-1]:
        binary_list[index - 1] = 1
    binary_list[-1] = 1
    return binary_list

ABLATION_CONFIGS = {
    "1. Utterance-level lexical baseline (Batch, r=3, no zscore, no merge)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3],
        alpha=0.5,
        normalize="minmax",
        min_segment_ratio=0.0,
        window_size=99999,
        stride=99998
    ),
    "2. + Sliding Window (W=40, S=5, r=3, no zscore, no merge)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3],
        alpha=0.5,
        normalize="minmax",
        min_segment_ratio=0.0,
        window_size=40,
        stride=5
    ),
    "3. + Local Z-score Normalization (W=40, S=5, r=3, Z-score, no merge)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3],
        alpha=1.2,
        normalize="zscore",
        min_segment_ratio=0.0,
        window_size=40,
        stride=5
    ),
    "4. + Multi-Scale Radii (W=40, S=5, r=[3,5,10,15,20], Z-score, no merge)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3, 5, 10, 15, 20],
        alpha=1.2,
        normalize="zscore",
        min_segment_ratio=0.0,
        window_size=40,
        stride=5
    ),
    "5. + Greedy Merging (Full Proposed Model)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3, 5, 10, 15, 20],
        alpha=1.2,
        normalize="zscore",
        min_segment_ratio=0.20,
        window_size=40,
        stride=5
    )
}

def evaluate_config_on_all(loader, config):
    all_pk, all_wd, all_f1 = [], [], []
    for corpus in Corpus:
        result = loader.load(corpus)
        tiler = SlidingTextTilingService(config=config)
        
        c_pk, c_wd, c_f1 = [], [], []
        for sample in result.samples:
            utterances = sample.utterances
            reference = sample.segment_sizes
            events = tiler.process(utterances)
            segments = [e.utterances_end - e.utterances_start + 1 for e in events]
            boundaries = [e.boundary_index for e in events]
            
            binary_labels = boundaries_to_binary(boundaries, len(utterances))
            ref_binary = segments_to_binary(reference)
            
            c_pk.append(float(segeval.pk(segments, reference)))
            c_wd.append(float(segeval.window_diff(segments, reference)))
            c_f1.append(float(f1_score(binary_labels, ref_binary, labels=[0, 1], average='macro')))
            
        all_pk.append(np.mean(c_pk))
        all_wd.append(np.mean(c_wd))
        all_f1.append(np.mean(c_f1))
        
    return np.mean(all_pk), np.mean(all_wd), np.mean(all_f1)

def main():
    data_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eval_vi")
    loader = EvalLoader(data_root)
    
    print("=" * 80)
    print("RUNNING ABLATION STUDY FOR MULTI-SCALE SLIDING TEXTTILING")
    print("=" * 80)
    
    results = {}
    for name, config in ABLATION_CONFIGS.items():
        print(f"Evaluating {name}...", end="", flush=True)
        pk, wd, f1 = evaluate_config_on_all(loader, config)
        results[name] = {"Pk": pk, "WD": wd, "F1": f1}
        print(f" -> Pk: {pk:.4f}, WD: {wd:.4f}, F1: {f1:.4f}")
        
    print("\nSUMMARY TABLE FOR THESIS:")
    print("| Biến thể (Ablation Variant) | $P_k$ TB ↓ | WD TB ↓ | Macro-$F_1$ TB ↑ | Nhận xét vai trò thành phần |")
    print("| :--- | ---: | ---: | ---: | :--- |")
    for name, m in results.items():
        print(f"| `{name}` | {m['Pk']:.4f} | {m['WD']:.4f} | {m['F1']:.4f} | |")

if __name__ == "__main__":
    main()
