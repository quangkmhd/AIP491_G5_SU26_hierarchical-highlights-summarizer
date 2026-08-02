import json
import sys
import os

# Add current path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.service.sliding_text_tiling import SlidingTextTilingService
from src.config.sliding_text_tiling import SlidingTextTilingConfig

# Define paths
EVAL_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/dialseg_711.json"
EVAL_OUTPUT_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/sliding_texttiling_segments_1_10_tool15.json"

def main():
    # Load dataset
    print(f"Loading evaluation dataset: {EVAL_FILE}")
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)

    target_dialogues = [d for d in dialogue_data if d.get('dial_id') is not None and 1 <= d.get('dial_id') <= 10]

    # Load the eval-run outputs we saved earlier
    print(f"Loading eval-run outputs: {EVAL_OUTPUT_FILE}")
    with open(EVAL_OUTPUT_FILE, 'r', encoding='utf-8') as f:
        eval_outputs = json.load(f)

    # This verification is segmentation-only; recap models are intentionally not loaded.
    config = SlidingTextTilingConfig(
        block_size=2,
        radii=[3, 5, 10, 15, 20],
        alpha=1.2,
        agg="mean",
        normalize="zscore",
        min_segment_ratio=0.2
    )
    tiler = SlidingTextTilingService(config=config)

    print("\nStarting 'real' production runs for dial_id 1 to 10...")
    all_matched = True

    for dialogue in target_dialogues:
        dial_id = str(dialogue['dial_id'])
        utterances_raw = dialogue['utterances']

        # Run the production lexical segmenter directly.
        segment_events = tiler.process(utterances_raw)

        # 3. Reconstruct segment sizes and ranges
        real_segments = [e.utterances_end - e.utterances_start + 1 for e in segment_events]
        real_ranges = [{"start": e.utterances_start, "end": e.utterances_end} for e in segment_events]

        # 4. Fetch the eval-run outputs for comparison
        eval_dialogue = eval_outputs[dial_id]
        eval_segments = eval_dialogue["predicted_segments_sizes"]
        eval_ranges = eval_dialogue["predicted_segments_ranges"]

        # 5. Compare outputs
        segments_match = real_segments == eval_segments
        ranges_match = real_ranges == eval_ranges

        print(f"Dial ID {dial_id}:")
        print(f"  Real Run Segments: {real_segments}")
        print(f"  Eval Run Segments: {eval_segments}")
        print(f"  Matches: Segments={segments_match}, Ranges={ranges_match}")

        if not (segments_match and ranges_match):
            all_matched = False
            print("  [ERROR] Output mismatch found!")

    print("\n" + "="*50)
    if all_matched:
        print("SUCCESS: Real run outputs are 100% identical to Eval run outputs!")
    else:
        print("FAILURE: There are mismatches between Real run and Eval run outputs.")
    print("="*50)

if __name__ == "__main__":
    main()
