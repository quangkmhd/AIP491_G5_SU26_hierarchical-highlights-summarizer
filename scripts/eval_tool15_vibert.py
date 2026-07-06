import os
import json
import torch
import numpy as np
from tqdm import tqdm
from transformers import AutoTokenizer
import segeval
from sklearn.metrics import f1_score

# Add current path to sys.path so we can import src
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.repo.model_loader import ModelLoader
from src.service.text_tiling import TextTilingService, boundaries_to_segments
from src.config.text_tiling import TextTilingConfig

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

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
BASE_MODEL = "FPTAI/vibert-base-cased"
CHECKPOINT_PATH = "/home/quangnhvn34/dev/me/AIP491/tools/09-meeting-recap-webapp/eval/Dialogue-Topic-Segmenter1/vibert_checkpoints_vi/cpt_4000.pth"
EVAL_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/dialseg_711.json"
OUTPUT_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/vibert_cpt4000_segments_1_10_tool15.json"

# Override NSP_CKPT_PATH in src.repo.coherence_net or model_loader to use the specific checkpoint
import src.repo.coherence_net
src.repo.coherence_net.NSP_CKPT_PATH = CHECKPOINT_PATH

# Fast similarity computing function using batch_size = 256 for efficiency
def fast_similarity_computing(texts, tokenizer, model, device):
    scores = []
    batch_size = 256
    with torch.no_grad():
        for i in range(0, len(texts)-1, batch_size):
            batch_pairs = []
            for j in range(i, min(i + batch_size, len(texts)-1)):
                sent1 = texts[j]
                sent2 = texts[j+1]
                tokenized = tokenizer(sent1, sent2, padding='max_length', max_length=128, truncation=True, return_tensors='pt')
                batch_pairs.append([tokenized, tokenized, tokenized])
            
            # Forward pass through CoherenceNet
            output = model(batch_pairs)
            coh_scores = output[:, 0, 0]  # Pos pair class 0 probability
            scores.extend(coh_scores.tolist())
    return scores

def run_alpha_search(dev_data, model, tokenizer):
    print(f"[INFO] Running alpha search on {len(dev_data)} DEV dialogues...")
    precomputed_dev_depth = []
    
    # We use depth_computing from text_tiling.py
    from src.service.text_tiling import depth_computing
    
    for dialogue in dev_data:
        similarity_scores = fast_similarity_computing(dialogue['utterances'], tokenizer, model, device)
        depth_scores = depth_computing(similarity_scores)
        precomputed_dev_depth.append(depth_scores)
        
    best_alpha = 0.0
    best_pk = float('inf')
    alphas = np.arange(-2.0, 2.0, 0.1)
    
    for alpha in alphas:
        total_pk = 0
        try:
            for idx, dialogue in enumerate(dev_data):
                depth_scores = precomputed_dev_depth[idx]
                
                # Re-implement the same threshold selection and boundary/segment conversion as in TextTilingService.process
                from src.service.text_tiling import cutoff_threshold
                tau = cutoff_threshold(depth_scores, alpha=alpha)
                
                boundaries = [i for i, d in enumerate(depth_scores) if d > tau]
                
                # Check for last boundary handling
                # In tool 15, SegmentEvent creation ends up adding n_utterances - 1 as boundary
                if not boundaries or boundaries[-1] < len(dialogue['utterances']) - 1:
                    boundaries.append(len(dialogue['utterances']) - 1)
                    
                segments = boundaries_to_segments(boundaries, len(dialogue['utterances']))
                pk = segeval.pk(segments, dialogue['segments'])
                total_pk += pk
            mean_pk = total_pk / len(dev_data)
            if mean_pk < best_pk:
                best_pk = mean_pk
                best_alpha = alpha
        except Exception as e:
            # Catch potential segeval exceptions if there are bugs in length matching
            print(f"[Error at alpha={alpha:.2f}]: {e}")
            
    print(f"-> Best alpha: {best_alpha:.2f} (DEV Pk: {best_pk:.4f})")
    return float(best_alpha)

def main():
    loader = ModelLoader.instance()
    handle = loader.load_coherence_net()
    model = handle.model
    tokenizer = handle.tokenizer
    device = handle.device
    
    print(f"Evaluating Dataset: {EVAL_FILE}")
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
        
    dev_data = [d for d in dialogue_data if d.get('set') == 'dev']
    target_dialogues = [d for d in dialogue_data if d.get('dial_id') is not None and 1 <= d.get('dial_id') <= 10]
    
    # Get best alpha using dev data
    best_alpha = run_alpha_search(dev_data, model, tokenizer)
    
    # Initialize TextTilingService with best_alpha
    config = TextTilingConfig(alpha=best_alpha)
    tiling_service = TextTilingService(config=config)
    
    ds_results = {}
    total_pk = 0.0
    total_wd = 0.0
    total_f1 = 0.0
    
    print(f"Evaluating {len(target_dialogues)} target dialogues (dial_id 1 to 10)...")
    for dialogue in tqdm(target_dialogues, desc="Eval"):
        dial_id = dialogue['dial_id']
        utterances = dialogue['utterances']
        reference = dialogue['segments']
        
        # Compute coherence scores
        scores = fast_similarity_computing(utterances, tokenizer, model, device)
        
        try:
            # Process using the TextTilingService of tool 15
            events = tiling_service.process(scores, len(utterances))
            
            # Convert events to segments
            segments = [e.utterances_end - e.utterances_start + 1 for e in events]
            
            # Map events to boundaries for F1 calculation
            # In neural_texttiling.py, binary_labels uses boundaries
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
    avg_pk = total_pk / num_samples
    avg_wd = total_wd / num_samples
    avg_f1 = total_f1 / num_samples
    
    print(f"\nResults for tool 15 (Avg of dial_id 1..10):")
    print(f"  Pk: {avg_pk:.4f}, WD: {avg_wd:.4f}, F1: {avg_f1:.4f}")
    
    # Save output to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(ds_results, f, indent=4, ensure_ascii=False)
    print(f"Saved detailed outputs to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
