import os
import json
import time
import sys
import numpy as np
import segeval
from sklearn.metrics import f1_score

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data import Corpus, EvalLoader
from src.service.sliding_text_tiling import SlidingTextTilingService
from src.config.sliding_text_tiling import SlidingTextTilingConfig

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

# Old metrics of sliding_texttiling (Ours) from the thesis tables
OLD_METRICS = {
    Corpus.DIALSEG_711.value: {"Pk": 0.3651, "WD": 0.3813, "F1": 0.3423},
    Corpus.DOC2DIAL.value: {"Pk": 0.5066, "WD": 0.5110, "F1": 0.2035},
    Corpus.MEETING_AMI.value: {"Pk": 0.5192, "WD": 0.5382, "F1": 0.0074},
    Corpus.MEETING_COMMITTEE.value: {"Pk": 0.4559, "WD": 0.4630, "F1": 0.0489},
    Corpus.MEETING_ICSI.value: {"Pk": 0.5382, "WD": 0.5519, "F1": 0.0044},
    Corpus.TIAGE.value: {"Pk": 0.4534, "WD": 0.4757, "F1": 0.1976},
}

# Config configurations to test
CONFIGS = {
    "Thesis Default (k=3, a=0.9, msr=0.08)": SlidingTextTilingConfig(
        block_size=3,
        radii=[3, 5, 10, 15, 20],
        alpha=0.9,
        agg="mean",
        normalize="zscore",
        min_segment_ratio=0.08
    ),
    "Code Default (k=2, a=1.0, msr=0.08)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3, 5, 10, 15, 20],
        alpha=1.0,
        agg="mean",
        normalize="zscore",
        min_segment_ratio=0.08
    ),
    "Optimized Params (k=2, a=1.2, msr=0.20)": SlidingTextTilingConfig(
        block_size=2,
        radii=[3, 5, 10, 15, 20],
        alpha=1.2,
        agg="mean",
        normalize="zscore",
        min_segment_ratio=0.20
    )
}

def evaluate_corpus(loader: EvalLoader, corpus: Corpus, config: SlidingTextTilingConfig):
    result = loader.load(corpus)
    tiler = SlidingTextTilingService(config=config)
    
    total_pk = 0.0
    total_wd = 0.0
    total_f1 = 0.0
    
    t0 = time.perf_counter()
    for sample in result.samples:
        utterances = sample.utterances
        reference = sample.segment_sizes
        
        events = tiler.process(utterances)
        segments = [e.utterances_end - e.utterances_start + 1 for e in events]
        boundaries = [e.boundary_index for e in events]
        
        binary_labels = boundaries_to_binary(boundaries, len(utterances))
        ref_binary = segments_to_binary(reference)
        
        pk = float(segeval.pk(segments, reference))
        wd = float(segeval.window_diff(segments, reference))
        f1 = float(f1_score(binary_labels, ref_binary, labels=[0, 1], average='macro'))
        
        total_pk += pk
        total_wd += wd
        total_f1 += f1
        
    elapsed = time.perf_counter() - t0
    n = len(result.samples)
    return {
        "Pk": total_pk / n if n else 0.0,
        "WD": total_wd / n if n else 0.0,
        "F1": total_f1 / n if n else 0.0,
        "time": elapsed
    }

def main():
    data_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eval_vi")
    loader = EvalLoader(data_root)
    
    print("=" * 80)
    print("RUNNING EVALUATION ON ALL 6 CORPORA")
    print("=" * 80)
    
    results = {}
    for config_name, config in CONFIGS.items():
        print(f"\nEvaluating with config: {config_name}")
        results[config_name] = {}
        for corpus in Corpus:
            print(f"  Processing {corpus.value}...", end="", flush=True)
            try:
                res = evaluate_corpus(loader, corpus, config)
                results[config_name][corpus.value] = res
                print(f" Done. Pk: {res['Pk']:.4f}, WD: {res['WD']:.4f}, F1: {res['F1']:.4f}, Time: {res['time']:.2f}s")
            except Exception as e:
                print(f" Error: {e}")
                
    # Generate comparative report
    print("\n" + "=" * 80)
    print("COMPARATIVE METRICS REPORT (NEW CODE VS OLD THESIS)")
    print("=" * 80)
    
    for corpus in Corpus:
        c_val = corpus.value
        old = OLD_METRICS.get(c_val, {"Pk": 0.0, "WD": 0.0, "F1": 0.0})
        print(f"\nCorpus: {c_val}")
        print(f"  Old Metrics (Thesis):   Pk: {old['Pk']:.4f}, WD: {old['WD']:.4f}, F1: {old['F1']:.4f}")
        for config_name in CONFIGS:
            new = results[config_name].get(c_val)
            if new:
                print(f"  {config_name:40s} Pk: {new['Pk']:.4f} ({new['Pk']-old['Pk']:+.4f}), WD: {new['WD']:.4f} ({new['WD']-old['WD']:+.4f}), F1: {new['F1']:.4f} ({new['F1']-old['F1']:+.4f})")
    
if __name__ == "__main__":
    main()
