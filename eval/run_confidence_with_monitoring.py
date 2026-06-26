#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import threading
import psutil
import requests

# Configuration
LOG_FILE_PATH = "/home/quangnhvn34/dev/me/AIP491/tools/09-meeting-recap-webapp/eval/run.log"
SHERPA_DIR = "/home/quangnhvn34/dev/me/AIP491/data/processed/output_sherpa"
SONIOX_DIR = "/home/quangnhvn34/dev/me/AIP491/data/processed/output_soniox"
OUTPUT_DIR = "eval/"
OLLAMA_MODEL = "gemma4:12b-it-qat"
MAX_WORKERS = 1
HANG_TIMEOUT_SECONDS = 180.0  # 3 minutes without progress is considered a hang

# Threading state
log_lock = threading.Lock()
last_progress_time = time.time()
stop_event = threading.Event()

def log_message(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    with log_lock:
        print(formatted_msg)
        sys.stdout.flush()
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}", file=sys.stderr)

def log_raw_subprocess_line(line: str):
    line = line.rstrip("\r\n")
    if not line:
        return
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [EVAL] {line}"
    with log_lock:
        print(formatted_msg)
        sys.stdout.flush()
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}", file=sys.stderr)

def get_gpu_info():
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if res.returncode == 0:
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                return {
                    "vram_used": int(parts[0]),
                    "vram_total": int(parts[1]),
                    "util": int(parts[2]),
                    "temp": int(parts[3])
                }
    except Exception:
        pass
    return None

def get_ram_info():
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "ram_used_gb": mem.used / (1024**3),
            "ram_total_gb": mem.total / (1024**3),
            "ram_pct": mem.percent,
            "swap_used_gb": swap.used / (1024**3),
            "swap_total_gb": swap.total / (1024**3),
            "swap_pct": swap.percent
        }
    except Exception:
        pass
    return None

def monitor_loop(process: subprocess.Popen):
    global last_progress_time
    log_message("[MONITOR] Starting GPU and system memory tracking...")
    
    # Initialize last_progress_time
    last_progress_time = time.time()
    
    while not stop_event.is_set():
        if process.poll() is not None:
            # Subprocess finished
            break
            
        gpu = get_gpu_info()
        ram = get_ram_info()
        
        gpu_str = "N/A"
        if gpu:
            gpu_str = f"Util: {gpu['util']}% | VRAM: {gpu['vram_used']}/{gpu['vram_total']} MiB | Temp: {gpu['temp']}°C"
            
        ram_str = "N/A"
        if ram:
            ram_str = f"RAM: {ram['ram_used_gb']:.2f}/{ram['ram_total_gb']:.2f} GiB ({ram['ram_pct']}%) | Swap: {ram['swap_used_gb']:.2f}/{ram['swap_total_gb']:.2f} GiB ({ram['swap_pct']}%)"
            
        log_message(f"[MONITOR] GPU -> {gpu_str} | System -> {ram_str}")
        
        # Check for hangs
        time_since_progress = time.time() - last_progress_time
        if time_since_progress > HANG_TIMEOUT_SECONDS:
            log_message(f"[CRITICAL] HANG DETECTED! No progress for {time_since_progress:.1f} seconds. Terminating subprocess to prevent system freeze.")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log_message("[CRITICAL] Subprocess did not terminate, killing it.")
                process.kill()
            break
            
        stop_event.wait(5.0)
    log_message("[MONITOR] Tracking stopped.")

def main():
    global last_progress_time
    
    # Clean/Reset log file at startup
    try:
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"--- LEXNORM CONFIDENCE EVAL RUN WITH GPU TRACKING - STARTED {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    except Exception as e:
        print(f"Error resetting log file: {e}", file=sys.stderr)
        
    # Unload model from Ollama first to free up VRAM/RAM
    log_message("[SYSTEM] Requesting Ollama to unload model to ensure a clean RAM/VRAM state...")
    try:
        resp = requests.post("http://127.0.0.1:11434/api/chat", json={"model": OLLAMA_MODEL, "keep_alive": 0}, timeout=5)
        if resp.status_code == 200:
            log_message("[SYSTEM] Ollama model unloaded successfully.")
        else:
            log_message(f"[SYSTEM] Ollama model unload returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_message(f"[WARNING] Failed to unload Ollama model: {e}")
        
    cmd = [
        "python", "-u", "-m", "eval.run_confidence_lexnorm_eval",
        "--sherpa-dir", SHERPA_DIR,
        "--soniox-dir", SONIOX_DIR,
        "--output-dir", OUTPUT_DIR,
        "--ollama-model", OLLAMA_MODEL,
        "--max-workers", str(MAX_WORKERS)
    ]
    
    log_message(f"[SYSTEM] Starting command: {' '.join(cmd)}")
    
    # Start subprocess
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Start monitor thread
    monitor_thread = threading.Thread(target=monitor_loop, args=(process,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        # Read stdout line by line
        for line in iter(process.stdout.readline, ""):
            log_raw_subprocess_line(line)
            
            # Check if line indicates evaluation progress, e.g. "[1/239] Corrected: ..."
            # or matches brackets like [12/239]
            if "Corrected:" in line or ("[" in line and "]" in line and "/" in line):
                last_progress_time = time.time()
                
        # Wait for the process to complete
        return_code = process.wait()
        log_message(f"[SYSTEM] Evaluation process finished with return code {return_code}")
    except KeyboardInterrupt:
        log_message("[SYSTEM] KeyboardInterrupt received. Terminating process...")
        process.terminate()
        process.wait()
        return 130
    finally:
        stop_event.set()
        monitor_thread.join(timeout=2)
        
    return return_code

if __name__ == "__main__":
    sys.exit(main())
