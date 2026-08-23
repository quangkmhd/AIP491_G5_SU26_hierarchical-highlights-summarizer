"""Detailed Diarization Inspector & Reporter.

Runs diarization on an input audio file, prints a clean terminal summary,
and outputs a comprehensive detailed JSON report (data/detailed_diarization_report.json).
"""

import argparse
import json
import logging
import os
import sys
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("diarization_inspector")

BASE_URL = "http://localhost:8002"


def main():
    parser = argparse.ArgumentParser(description="SD-Module Detailed Diarization Inspector")
    parser.add_argument("--audio", type=str, default="data/overlap-audio-sample.wav", help="Path to input audio file")
    parser.add_argument("--report", type=str, default="data/detailed_diarization_report.json", help="Path to save detailed JSON report")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        logger.error(f"Audio file not found: {args.audio}")
        sys.exit(1)

    logger.info(f"Sending audio file to SD-Module API: {args.audio}")
    url = f"{BASE_URL}/api/v1/diarize"
    
    with open(args.audio, "rb") as f:
        files = {"file": (os.path.basename(args.audio), f, "audio/wav")}
        res = requests.post(url, files=files)

    if res.status_code != 200:
        logger.error(f"API Error ({res.status_code}): {res.text}")
        sys.exit(1)

    data = res.json()
    segments = data.get("segments", data.get("chunks", []))
    duration = data.get("duration_seconds", 0)
    proc_time = data.get("processing_time_seconds", 0)

    # 1. Print Terminal Summary
    print("\n==========================================================================")
    print("                    SPEAKER DIARIZATION SUMMARY REPORT                    ")
    print("==========================================================================")
    print(f"Status:                 {data.get('status')}")
    print(f"Audio Duration:         {duration} seconds ({round(duration/60, 2)} minutes)")
    print(f"Total Processing Time:  {proc_time} seconds")
    print(f"Total Speech Segments:  {len(segments)}")

    # Branch counts
    branch_counts = {}
    speaker_counts = {}
    overlap_count = 0
    for s in segments:
        b = s.get("branch", "UNKNOWN")
        branch_counts[b] = branch_counts.get(b, 0) + 1
        if s.get("has_overlap"):
            overlap_count += 1
        for spk in s.get("speakers", []):
            speaker_counts[spk] = speaker_counts.get(spk, 0) + 1

    print("\nDecision Branch Breakdown:")
    for branch, count in branch_counts.items():
        print(f"  - {branch:<16}: {count} segments")
    print(f"Total Overlapping Segments: {overlap_count}")

    print("\nSpeaker Attribution Count:")
    for spk, count in speaker_counts.items():
        print(f"  - {spk:<16}: {count} segments")

    print("\n" + "-" * 85)
    print("%-10s %-10s %-16s %-20s %-12s" % ("Start (s)", "End (s)", "Branch", "Speakers", "Overlap?"))
    print("-" * 85)
    for s in segments:
        spk_str = ", ".join(s.get("speakers", []))
        print("%-10s %-10s %-16s %-20s %-12s" % (
            s.get("start_time"),
            s.get("end_time"),
            s.get("branch"),
            spk_str,
            "YES ⚡" if s.get("has_overlap") else "No"
        ))
        for t in s.get("speaker_timestamps", []):
            print("    └── %-16s: %ss -> %ss (duration: %ss)" % (
                t.get("speaker"),
                t.get("start_time"),
                t.get("end_time"),
                t.get("speech_duration_sec")
            ))

    # 2. Build Detailed JSON Report File
    detailed_segments = []
    for s in segments:
        detailed_segments.append({
            "chunk_index": s.get("chunk_index"),
            "start_time": s.get("start_time"),
            "end_time": s.get("end_time"),
            "duration_sec": round(s.get("end_time", 0) - s.get("start_time", 0), 3),
            "branch": s.get("branch"),
            "has_overlap": s.get("has_overlap"),
            "speakers": s.get("speakers"),
            "speaker_timestamps": s.get("speaker_timestamps", []),
            "separated_streams_count": len(s.get("audio_streams_b64", [])),
            "audio_streams_b64": s.get("audio_streams_b64", [])
        })

    # Read voiceprint pool state from disk if available
    pool_meta_path = "results/pool_state/pool_metadata.json"
    pool_meta = {}
    if os.path.exists(pool_meta_path):
        try:
            with open(pool_meta_path, "r", encoding="utf-8") as pf:
                pool_meta = json.load(pf)
        except Exception:
            pass

    report = {
        "status": data.get("status"),
        "audio_file": args.audio,
        "duration_seconds": duration,
        "processing_time_seconds": proc_time,
        "total_segments": len(segments),
        "branch_summary": branch_counts,
        "speaker_summary": speaker_counts,
        "active_voiceprint_profiles": pool_meta,
        "detailed_segments": detailed_segments
    }

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as rf:
        json.dump(report, rf, indent=4, ensure_ascii=False)

    print("\n==========================================================================")
    logger.info(f"Detailed inspection report saved to: {args.report}")
    print("==========================================================================\n")


if __name__ == "__main__":
    main()
