import os
import json
import numpy as np
from tqdm import tqdm
import segeval
from sklearn.metrics import f1_score

# Add current path to sys.path so we can import src
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

# Define evaluation settings
EVAL_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/dialseg_711.json"
OUTPUT_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/sliding_texttiling_segments_1_10_tool15.json"

def run_param_search(dev_data):
    """Grid-search best parameters on dev set using the sliding TextTiling pipeline."""
    print(f"[INFO] Running parameter search on {len(dev_data)} DEV dialogues...")

    best_pk = float("inf")
    best_params = {"block_size": 3, "alpha": 0.9, "radii": [3, 5, 10, 15, 20],
                   "agg": "mean", "normalize": "zscore", "min_segment_ratio": 0.08}

    radii_options = [
        [3, 5, 10, 15, 20],
        [5, 10, 15],
    ]
    agg_options = ["mean", "max"]
    normalize_options = ["zscore", "minmax"]

    for block_size in [1, 2, 3]:
        for radii in radii_options:
            for alpha in [0.5, 0.8, 1.0, 1.2, 1.5]:
                for agg in agg_options:
                    for norm in normalize_options:
                        for msr in [0.05, 0.08, 0.10, 0.20]:
                            total_pk = 0.0
                            try:
                                cfg = SlidingTextTilingConfig(
                                    block_size=block_size,
                                    radii=radii,
                                    alpha=alpha,
                                    agg=agg,
                                    normalize=norm,
                                    min_segment_ratio=msr,
                                )
                                tiler = SlidingTextTilingService(config=cfg)
                                for dialogue in dev_data:
                                    segs = [e.utterances_end - e.utterances_start + 1
                                            for e in tiler.process(dialogue['utterances'])]
                                    pk = float(segeval.pk(segs, dialogue['segments']))
                                    total_pk += pk
                                mean_pk = total_pk / max(len(dev_data), 1)
                                if mean_pk < best_pk:
                                    best_pk = mean_pk
                                    best_params = {
                                        "block_size": block_size,
                                        "radii": radii,
                                        "alpha": alpha,
                                        "agg": agg,
                                        "normalize": norm,
                                        "min_segment_ratio": msr,
                                    }
                            except Exception as e:
                                print(f"[Error at params block={block_size} radii={radii} "
                                      f"alpha={alpha} agg={agg} norm={norm} msr={msr}]: {e}")

    print(f"-> Best params: {best_params} (DEV Pk: {best_pk:.4f})")
    return best_params

def main():
    print(f"Evaluating Dataset: {EVAL_FILE}")
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)

    dev_data = [d for d in dialogue_data if d.get('set') == 'dev']
    target_dialogues = [d for d in dialogue_data if d.get('dial_id') is not None and 1 <= d.get('dial_id') <= 10]

    # Get best params using dev data
    best_params = run_param_search(dev_data)

    # Initialize SlidingTextTilingService with best params
    config = SlidingTextTilingConfig(
        block_size=best_params["block_size"],
        radii=best_params["radii"],
        alpha=best_params["alpha"],
        agg=best_params["agg"],
        normalize=best_params["normalize"],
        min_segment_ratio=best_params["min_segment_ratio"],
    )
    tiling_service = SlidingTextTilingService(config=config)

    ds_results = {}
    total_pk = 0.0
    total_wd = 0.0
    total_f1 = 0.0

    print(f"Evaluating {len(target_dialogues)} target dialogues (dial_id 1 to 10)...")
    for dialogue in tqdm(target_dialogues, desc="Eval"):
        dial_id = dialogue['dial_id']
        utterances = dialogue['utterances']
        reference = dialogue['segments']

        try:
            # Process using the SlidingTextTilingService (takes utterances directly)
            events = tiling_service.process(utterances)

            # Convert events to segments
            segments = [e.utterances_end - e.utterances_start + 1 for e in events]

            # Map events to boundaries for F1 calculation
            boundaries = [e.boundary_index for e in events]

            binary_labels = boundaries_to_binary(boundaries, len(utterances))

            pk = float(segeval.pk(segments, reference))
            wd = float(segeval.window_diff(segments, reference))
            f1 = float(f1_score(binary_labels, segments_to_binary(reference), labels=[0, 1], average='macro'))

            total_pk += pk
            total_wd += wd
            total_f1 += f1

            ranges = [{"start": e.utterances_start, "end": e.utterances_end} for e in events]
            segmented_utts = [utterances[e.utterances_start:e.utterances_end+1] for e in events]

            ds_results[str(dial_id)] = {
                "evaluation_scores": {
                    "Pk": pk,
                    "WD": wd,
                    "F1": f1
                },
                "predicted_segments_sizes": segments,
                "predicted_boundaries_utterance_indices": boundaries,
                "predicted_segments_ranges": ranges,
                "ground_truth_segments_sizes": reference,
                "segmented_utterances": segmented_utts
            }
        except Exception as e:
            print(f"\n[Error at dial_id={dial_id}]: {e}")
            import traceback
            traceback.print_exc()

    num_samples = len(target_dialogues)
    avg_pk = total_pk / num_samples if num_samples else 0
    avg_wd = total_wd / num_samples if num_samples else 0
    avg_f1 = total_f1 / num_samples if num_samples else 0

    print(f"\nResults for tool 15 (Sliding TextTiling, dial_id 1..10):")
    print(f"  Pk: {avg_pk:.4f}, WD: {avg_wd:.4f}, F1: {avg_f1:.4f}")

    # Save output to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(ds_results, f, indent=4, ensure_ascii=False)
    print(f"Saved detailed outputs to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()