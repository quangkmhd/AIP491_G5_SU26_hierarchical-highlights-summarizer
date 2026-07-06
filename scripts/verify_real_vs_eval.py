import os
import json
import torch
import sys

# Set env to mock LLM loading so we don't load/download Gemma weights
os.environ["MODEL_LOAD_LLM"] = "0"

# Add current path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.repo.model_loader import ModelLoader
from src.service.meeting_recap_orchestrator import StreamingOrchestrator, RecapEventType
from src.service.text_tiling import TextTilingService
from src.config.text_tiling import TextTilingConfig
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Define paths
CHECKPOINT_PATH = "/home/quangnhvn34/dev/me/AIP491/tools/09-meeting-recap-webapp/eval/Dialogue-Topic-Segmenter1/vibert_checkpoints_vi/cpt_4000.pth"
EVAL_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/dialseg_711.json"
EVAL_OUTPUT_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/vibert_cpt4000_segments_1_10_tool15.json"

# Override NSP_CKPT_PATH to use the correct checkpoint
import src.repo.coherence_net
src.repo.coherence_net.NSP_CKPT_PATH = CHECKPOINT_PATH

def main():
    # Load model and tokenizer
    loader = ModelLoader.instance()
    handle = loader.load_coherence_net()
    scorer = handle.model
    tokenizer = handle.tokenizer
    
    # Load dataset
    print(f"Loading evaluation dataset: {EVAL_FILE}")
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
        
    target_dialogues = [d for d in dialogue_data if d.get('dial_id') is not None and 1 <= d.get('dial_id') <= 10]
    
    # Load the eval-run outputs we saved earlier
    print(f"Loading eval-run outputs: {EVAL_OUTPUT_FILE}")
    with open(EVAL_OUTPUT_FILE, 'r', encoding='utf-8') as f:
        eval_outputs = json.load(f)
        
    # We instantiate the StreamingOrchestrator with alpha = 1.5 (best alpha from eval)
    config = TextTilingConfig(alpha=1.5)
    tiler = TextTilingService(config=config)
    orchestrator = StreamingOrchestrator(tiler=tiler)
    
    print("\nStarting 'real' production runs for dial_id 1 to 10...")
    all_matched = True
    
    for dialogue in target_dialogues:
        dial_id = str(dialogue['dial_id'])
        utterances_raw = dialogue['utterances']
        
        # 1. Convert to DialogueTranscript format
        utterances_obj = []
        for idx, text in enumerate(utterances_raw):
            utterances_obj.append(Utterance(
                speaker=f"Speaker_{idx % 2}",
                text=text,
                index=idx
            ))
        transcript = DialogueTranscript(utterances=utterances_obj)
        
        # 2. Run real production orchestrator stream
        # Collect SEGMENT_CLOSED events to get the predicted segments
        segment_events = []
        for event in orchestrator.process_stream(transcript):
            if event.type == RecapEventType.SEGMENT_CLOSED:
                segment_events.append(event)
                
        # 3. Reconstruct segment sizes and ranges
        real_segments = [e.data['utterances_end'] - e.data['utterances_start'] + 1 for e in segment_events]
        real_ranges = [{"start": e.data['utterances_start'], "end": e.data['utterances_end']} for e in segment_events]
        
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
