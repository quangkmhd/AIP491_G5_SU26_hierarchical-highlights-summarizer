"""End-to-End Meeting Pipeline Runner (sd-module + asr-module).

Chains Speaker Diarization (Port 8002) and Speech-to-Text Transcription (Port 8000)
to produce a complete structured meeting transcript JSON file.
"""

import argparse
import base64
import io
import json
import logging
import os
import sys
import time
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("meeting_pipeline")

SD_URL = "http://localhost:8002/api/v1/diarize"
ASR_URL = "http://localhost:8000/api/v1/transcribe"


def main():
    parser = argparse.ArgumentParser(description="SD-Module + ASR-Module End-to-End Pipeline")
    parser.add_argument("--audio", type=str, default="data/overlap-audio-sample.wav", help="Path to input audio file")
    parser.add_argument("--output", type=str, default="data/full_meeting_transcript.json", help="Path to save output transcript JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        logger.error(f"Audio file not found: {args.audio}")
        sys.exit(1)

    t_start = time.perf_counter()

    # Step 1: Call SD-Module (Port 8002)
    logger.info(f"1. Sending audio to SD-Module (Port 8002) for Diarization: {args.audio}")
    with open(args.audio, "rb") as f:
        sd_res = requests.post(SD_URL, files={"file": (os.path.basename(args.audio), f, "audio/wav")})

    if sd_res.status_code != 200:
        logger.error(f"SD-Module Error ({sd_res.status_code}): {sd_res.text}")
        sys.exit(1)

    sd_data = sd_res.json()
    segments = sd_data.get("segments", sd_data.get("chunks", []))
    duration = sd_data.get("duration_seconds", 0)
    logger.info(f"Diarization complete! Received {len(segments)} segments ({duration}s audio).")

    # Step 2: Call ASR-Module (Port 8000) for each separated audio stream in RAM
    logger.info("2. Transcribing audio streams via ASR-Module (Port 8000)...")
    transcript_items = []
    speakers_set = set()

    print("\n" + "=" * 80)
    print("                        MEETING TRANSCRIPT SUMMARY                        ")
    print("=" * 80)

    for seg_idx, seg in enumerate(segments):
        start_t = seg.get("start_time")
        end_t = seg.get("end_time")
        branch = seg.get("branch")
        has_overlap = seg.get("has_overlap", False)
        speakers = seg.get("speakers", [])
        spk_timestamps = seg.get("speaker_timestamps", [])
        b64_streams = seg.get("audio_streams_b64", [])

        for s_idx, (spk, b64_str) in enumerate(zip(speakers, b64_streams)):
            speakers_set.add(spk)
            wav_bytes = base64.b64decode(b64_str)
            files = {"file": (f"segment_{seg_idx}_{spk}_{s_idx}.wav", io.BytesIO(wav_bytes), "audio/wav")}

            try:
                asr_res = requests.post(ASR_URL, files=files)
                if asr_res.status_code == 200:
                    text = asr_res.json().get("text", "")
                else:
                    text = f"[ASR Error {asr_res.status_code}]"
            except Exception as e:
                text = f"[ASR Connection Failed: {e}]"

            # Determine specific start/end timestamp for this speaker if available
            spk_start = start_t
            spk_end = end_t
            if s_idx < len(spk_timestamps):
                spk_start = spk_timestamps[s_idx].get("start_time", start_t)
                spk_end = spk_timestamps[s_idx].get("end_time", end_t)

            item = {
                "segment_id": len(transcript_items),
                "start_time": spk_start,
                "end_time": spk_end,
                "speaker": spk,
                "text": text,
                "has_overlap": has_overlap,
                "branch": branch
            }
            transcript_items.append(item)

            overlap_tag = " [OVERLAP ⚡]" if has_overlap else ""
            print(f"[{spk_start:>5.1f}s -> {spk_end:>5.1f}s] {spk:<10}{overlap_tag}: {text}")

    print("=" * 80 + "\n")

    total_proc_time = round(time.perf_counter() - t_start, 3)

    # Step 3: Build Complete Output JSON
    output_json = {
        "status": "success",
        "meeting_metadata": {
            "audio_file": args.audio,
            "duration_seconds": duration,
            "pipeline_execution_time_seconds": total_proc_time,
            "total_segments": len(transcript_items),
            "speakers_count": len(speakers_set),
            "speakers_list": sorted(list(speakers_set))
        },
        "transcript_segments": transcript_items
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as out_f:
        json.dump(output_json, out_f, indent=2, ensure_ascii=False)

    logger.info(f"Full Meeting Transcript JSON successfully saved to: {args.output}")


if __name__ == "__main__":
    main()
