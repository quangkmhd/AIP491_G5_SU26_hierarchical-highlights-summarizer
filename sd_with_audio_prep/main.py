import argparse
import numpy as np
import soundfile as sf
import json
import logging
import sys
import time
import os
from scipy import signal

from config.di_container import DIContainer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

def main():
    parser = argparse.ArgumentParser(description="Target Diarization Pipeline - End-to-End Execution")
    parser.add_argument("--audio", type=str, required=True, help="Path to the input audio file")
    parser.add_argument("--output", type=str, default="diarization_output.json", help="Path to save the JSON output (default: diarization_output.json)")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        logger.error(f"File not found: {args.audio}")
        sys.exit(1)

    logger.info("Initializing AI system (DI Container)...")
    start_init = time.time()
    container = DIContainer()
    logger.info(f"Initialized successfully in {time.time() - start_init:.2f}s")

    sr = container.config.get("audio", {}).get("sample_rate", 16000)
    cfg_buffer = container.config.get("module2_diarization", {}).get("smart_buffer", {})
    frame_size_ms = cfg_buffer.get("chunk_size_ms", 500)
    frame_size = int(sr * frame_size_ms / 1000)

    logger.info(f"Loading audio file: {args.audio}")
    try:
        audio, orig_sr = sf.read(args.audio)
        # Convert to mono if multi-channel
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Resample to system standard (16000 Hz)
        if orig_sr != sr:
            num_samples = int(len(audio) * sr / orig_sr)
            audio = signal.resample(audio, num_samples)
    except Exception as e:
        logger.error(f"Error loading audio file: {e}")
        sys.exit(1)

    duration = len(audio) / sr
    logger.info(f"Audio loaded. Duration: {duration:.2f}s. Starting processing...")

    output_dir = "output_chunks"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Separated audio chunks will be saved to: {output_dir}/")

    results = []
    start_proc = time.time()
    
    # 1. Chop the audio into chunks and feed it into the pipeline (Streaming simulation)
    for j in range(0, len(audio), frame_size):
        frame = audio[j:j+frame_size]
        if len(frame) < frame_size:
            # Zero-pad the last frame if it's smaller than the frame size
            frame = np.pad(frame, (0, frame_size - len(frame)))
            
        res1 = container.module1.process_chunk(frame)
        
        # When the buffer reaches the cut threshold
        if res1 and res1["status"] != "BUFFERING":
            if res1["status"] == "PASS":
                res2 = container.module2.process(
                    res1["clean_audio"], res1["t_d"], res1["t_c"]
                )
                
                start_time = float(res1["t_d"])
                end_time = float(res1["t_d"]) + float(len(res1["clean_audio"])/sr)
                
                segment_audio_paths = []
                # Save each separated stream to a WAV file
                for i, (speaker, audio_array) in enumerate(zip(res2["speakers"], res2.get("audio_streams", []))):
                    chunk_filename = os.path.join(output_dir, f"{int(start_time*1000)}_{int(end_time*1000)}_{speaker}_{i}.wav")
                    sf.write(chunk_filename, audio_array, sr)
                    segment_audio_paths.append(chunk_filename)
                
                results.append({
                    "start_time": round(start_time, 3),
                    "end_time": round(end_time, 3),
                    "branch": res2["branch"],
                    "speakers": res2["speakers"],
                    "has_overlap": res2.get("has_overlap", False),
                    "audio_files": segment_audio_paths
                })
                logger.info(f"[{start_time:.1f}s - {end_time:.1f}s] {res2['branch']} | Speakers: {res2['speakers']}")

    # 2. Force flush any remaining audio in the Buffer
    res1 = container.module1.flush()
    if res1 and res1["status"] != "BUFFERING" and res1["status"] == "PASS":
        res2 = container.module2.process(
            res1["clean_audio"], res1["t_d"], res1["t_c"]
        )
        start_time = float(res1["t_d"])
        end_time = float(res1["t_d"]) + float(len(res1["clean_audio"])/sr)
        
        segment_audio_paths = []
        for i, (speaker, audio_array) in enumerate(zip(res2["speakers"], res2.get("audio_streams", []))):
            chunk_filename = os.path.join(output_dir, f"{int(start_time*1000)}_{int(end_time*1000)}_{speaker}_{i}.wav")
            sf.write(chunk_filename, audio_array, sr)
            segment_audio_paths.append(chunk_filename)
        
        results.append({
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
            "branch": res2["branch"],
            "speakers": res2["speakers"],
            "has_overlap": res2.get("has_overlap", False),
            "audio_files": segment_audio_paths
        })
        logger.info(f"[{start_time:.1f}s - {end_time:.1f}s] {res2['branch']} | Speakers: {res2['speakers']}")

    elapsed = time.time() - start_proc
    logger.info(f"Processing completed in {elapsed:.2f}s (Real-Time Factor: {elapsed/duration:.2f})")

    # 3. Package output into structured JSON
    output_data = {
        "audio_file": args.audio,
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "total_segments_processed": len(results),
        "status": "success",
        "segments": results
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Detailed results saved to: {args.output}")

if __name__ == "__main__":
    main()
