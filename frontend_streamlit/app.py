import os
import time
import requests
import streamlit as st
import streamlit.components.v1 as components
from frontend_streamlit.live_api import finalize_live_session, summary_cards

# Gateway backend configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# Page Configuration
st.set_page_config(
    page_title="AI Meeting Intelligence Platform",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS Styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .speaker-badge-01 {
        background-color: #1e3a8a;
        color: #93c5fd;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .speaker-badge-02 {
        background-color: #064e3b;
        color: #6ee7b7;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .speaker-badge-default {
        background-color: #4c1d95;
        color: #c084fc;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .transcript-card {
        background-color: #1f2937;
        padding: 14px;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 10px;
    }
    .summary-box {
        background-color: #1e1b4b;
        padding: 16px;
        border-radius: 8px;
        border-left: 4px solid #8b5cf6;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State Variables
if "live_meeting_active" not in st.session_state:
    st.session_state["live_meeting_active"] = False
if "live_session_id" not in st.session_state:
    st.session_state["live_session_id"] = None

# Sidebar Control
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/microphone.png", width=64)
    st.title("Meeting Intelligence")
    st.caption("Central Gateway: `http://localhost:8080`")

    st.divider()

    # Backend Liveness Check
    backend_online = False
    for _ in range(3):
        try:
            health_res = requests.get(f"{BACKEND_URL}/health", timeout=2.0)
            if health_res.status_code == 200 and health_res.json().get("status") == "healthy":
                backend_online = True
                break
        except Exception:
            time.sleep(0.5)

    if backend_online:
        st.success("🟢 Backend Gateway Online")
    else:
        st.error("🔴 Backend Gateway Offline")

    st.divider()
    st.markdown("### 🧩 AI Microservices")
    st.markdown("- **`asr-module`** (Port 8000): Sherpa-ONNX Zipformer")
    st.markdown("- **`sd-module`** (Port 8002): Diarization & BSS/TSE")
    st.markdown("- **`llms-module`** (Port 8003): ViT5 + BARTpho Summaries")

# Main Title Header
st.title("🎙️ AI Meeting Intelligence Platform")
st.subheader("Automated Speaker Diarization, Speech-to-Text, and Topic Segmentation")

st.markdown("---")

# Main 3-Tab Navigation Bar
nav_upload, nav_online, nav_history = st.tabs([
    "📁 Meeting Upload",
    "📹 Meeting Online",
    "📜 Meeting History",
])


# -----------------------------------------------------------------------------
# TAB 1: MEETING UPLOAD (OFFLINE RECORDINGS)
# -----------------------------------------------------------------------------
with nav_upload:
    st.markdown("### 📁 Upload Offline Meeting Audio File")
    st.caption("Upload recorded meeting audio (`.wav`, `.mp3`, `.flac`) for pipeline diarization, ASR, and LLM summarization.")

    uploaded_file = st.file_uploader(
        "Select Audio Recording File",
        type=["wav", "mp3", "flac", "m4a"],
        key="offline_uploader",
    )

    offline_title = st.text_input("Meeting Session Title", placeholder="e.g. Q3 Architecture Review", key="offline_title")

    if uploaded_file and st.button("🚀 Start Pipeline Processing", type="primary", key="offline_btn"):
        st.audio(uploaded_file, format="audio/wav")
        with st.spinner("Uploading file and launching AI processing pipeline..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                payload = {
                    "title": offline_title or uploaded_file.name,
                    "meeting_type": "offline_upload",
                }
                res = requests.post(f"{BACKEND_URL}/api/v1/sessions", files=files, data=payload, timeout=30.0)

                if res.status_code == 201:
                    sid = res.json().get("session", {}).get("session_id")
                    st.success(f"Pipeline started! Session ID: `{sid}`")

                    # Poll progress
                    prog_bar = st.progress(0, text="Processing...")
                    while True:
                        s_data = requests.get(f"{BACKEND_URL}/api/v1/sessions/{sid}").json()
                        s_info = s_data.get("session", {})
                        pct = int(s_info.get("progress_percentage", 0))
                        status = s_info.get("status", "created")

                        prog_bar.progress(pct, text=f"Stage: **{status.upper()}** ({pct}%)")

                        if status == "completed":
                            st.success("Meeting analysis completed!")
                            col_utts, col_summ = st.columns([1, 1])

                            with col_utts:
                                st.markdown("#### 🗣️ Diarized Transcript")
                                for u in s_data.get("utterances", []):
                                    st.markdown(
                                        f"""
                                        <div class="transcript-card">
                                            <span class="speaker-badge-01">{u.get('speaker_id')}</span>
                                            <span style="font-size:0.8rem; color:#9ca3af; margin-left:8px;">{u.get('start_time')}s - {u.get('end_time')}s</span>
                                            <p style="margin-top:6px;">{u.get('text')}</p>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                            with col_summ:
                                st.markdown("#### 📌 Hierarchical LLM Summary")
                                summ = s_data.get("summary", {})
                                for chapter_title, chunk_summary in summary_cards(summ):
                                    with st.expander(f"📖 {chapter_title}", expanded=True):
                                        st.write(chunk_summary)
                            break

                        elif status == "failed":
                            st.error(f"Error: {s_info.get('error_message')}")
                            break

                        time.sleep(1.0)
                else:
                    st.error(f"Failed to create session: {res.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")


# -----------------------------------------------------------------------------
# TAB 2: MEETING ONLINE (GOOGLE MEET-STYLE SPLIT UI)
# -----------------------------------------------------------------------------
with nav_online:
    st.markdown("### 📹 Live Online Meeting Workspace")
    st.caption("Real-time speech transcription (Left 50%) & dynamic LLM topic summaries (Right 50%).")

    online_title = st.text_input("Live Meeting Title", value="Weekly Team Sync", key="online_title")

    col_ctrl1, col_ctrl2 = st.columns([1, 3])
    with col_ctrl1:
        if not st.session_state["live_meeting_active"]:
            if st.button("🟢 Start Online Meeting", type="primary", use_container_width=True):
                try:
                    payload = {
                        "title": online_title,
                        "meeting_type": "online_live",
                    }
                    res = requests.post(f"{BACKEND_URL}/api/v1/sessions", data=payload, timeout=10.0)
                    if res.status_code == 201:
                        st.session_state["live_session_id"] = res.json()["session"]["session_id"]
                        st.session_state["live_meeting_active"] = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to start live session: {e}")
        else:
            if st.button("🔴 Stop & Finalize Meeting", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Finalizing trailing speech and topic segments..."):
                        finalize_live_session(
                            BACKEND_URL,
                            st.session_state["live_session_id"],
                        )
                    st.session_state["live_meeting_active"] = False
                    st.success("Meeting finalized successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to finalize meeting: {exc}")

    with col_ctrl2:
        if st.session_state["live_meeting_active"]:
            st.success(f"🔴 LIVE MEETING IN PROGRESS (Session: `{st.session_state['live_session_id']}`)")

    st.divider()

    # 50/50 SPLIT SCREEN LAYOUT
    left_col, right_col = st.columns([1, 1])

    # LEFT HALF (50%): LIVE TRANSCRIPT STREAM
    with left_col:
        st.markdown("### 🎙️ Live Speech Transcript")
        if st.session_state["live_meeting_active"]:
            sid = st.session_state["live_session_id"]

            st.caption("🟢 **Live Meeting Connected**. Audio frames are streamed automatically to Backend Gateway.")
            
            # Input Mode Switch: Live Mic Audio or Live Audio Sample Streamer
            stream_source = st.radio(
                "Streaming Source",
                ["Microphone Stream", "Stream Live Audio Sample File"],
                horizontal=True,
                key="stream_source_choice"
            )

            if stream_source == "Microphone Stream":
                components.html(
                    f"""
                    <div style="background-color:#1e293b; padding:12px; border-radius:8px; color:#e2e8f0; font-family:sans-serif; text-align:center; border-left:4px solid #10b981;">
                        <div id="status-indicator" style="font-weight:bold; color:#10b981; margin-bottom:4px; font-size:0.95rem;">
                            🔴 Hands-Free Live Stream Active (Auto-chunking every 3.5s)
                        </div>
                        <div style="font-size:0.8rem; color:#94a3b8;">
                            Speak into your microphone. Speech frames stream automatically to backend.
                        </div>
                    </div>
                    <script>
                    (function() {{
                        let sessionId = "{sid}";
                        let backendUrl = "{BACKEND_URL}";
                        
                        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
                            document.getElementById('status-indicator').innerHTML = '⚠️ Browser MediaDevices API not supported';
                            return;
                        }}

                        navigator.mediaDevices.getUserMedia({{ audio: true }})
                            .then(stream => {{
                                let mediaRecorder;
                                
                                function startRecording() {{
                                    mediaRecorder = new MediaRecorder(stream);
                                    let chunks = [];
                                    mediaRecorder.ondataavailable = function(e) {{
                                        if (e.data && e.data.size > 0) {{
                                            chunks.push(e.data);
                                        }}
                                    }};
                                    mediaRecorder.onstop = function() {{
                                        let blob = new Blob(chunks, {{ type: mediaRecorder.mimeType }});
                                        if (blob.size > 0) {{
                                            let formData = new FormData();
                                            formData.append('file', blob, 'live_stream_chunk.wav');
                                            fetch(backendUrl + '/api/v1/sessions/' + sessionId + '/audio', {{
                                                method: 'POST',
                                                body: formData
                                            }}).then(res => {{
                                                console.log('Live stream chunk sent successfully:', res.status);
                                            }}).catch(err => {{
                                                console.error('Live stream chunk error:', err);
                                            }});
                                        }}
                                        // Start next recording slice immediately
                                        startRecording();
                                    }};
                                    
                                    mediaRecorder.start();
                                    
                                    // Stop after 3.5 seconds to trigger onstop
                                    setTimeout(() => {{
                                        if (mediaRecorder.state === "recording") {{
                                            mediaRecorder.stop();
                                        }}
                                    }}, 3500);
                                }}
                                
                                startRecording();
                            }})
                            .catch(err => {{
                                document.getElementById('status-indicator').innerHTML = '🔴 Mic Access Error: ' + err.message;
                            }});
                    }})();
                    </script>
                    """,
                    height=85,
                )

            elif stream_source == "Stream Live Audio Sample File":
                st.info("Simulating continuous real-time live meeting audio stream (3-second chunks).")
                if st.button("▶ Stream 3-Second Chunk to Pipeline", type="primary", key="stream_chunk_btn"):
                    # Stream live sample audio chunk
                    sample_file = "backend/sd-module/data/overlap-audio-sample.wav"
                    if not os.path.exists(sample_file):
                        sample_file = "backend/asr-module/data/audio-sample.wav"
                    
                    if os.path.exists(sample_file):
                        with open(sample_file, "rb") as f:
                            c_bytes = f.read()
                        with st.spinner("⚡ Streaming chunk -> Diarization -> ASR..."):
                            files = {"file": ("live_stream_chunk.wav", c_bytes[:96000], "audio/wav")} # 3s frame
                            res = requests.post(f"{BACKEND_URL}/api/v1/sessions/{sid}/audio", files=files, timeout=60.0)
                            if res.status_code == 200:
                                st.toast("3-Second live stream chunk processed!", icon="⚡")
                                st.rerun()

            # Render Live Transcribed Utterance Cards
            if sid:
                try:
                    s_data = requests.get(f"{BACKEND_URL}/api/v1/sessions/{sid}", timeout=5.0).json()
                    utts = s_data.get("utterances", [])
                    if utts:
                        for u in utts:
                            spk = u.get("speaker_id", "Speaker")
                            badge = "speaker-badge-01" if "01" in spk else ("speaker-badge-02" if "02" in spk else "speaker-badge-default")
                            ov_tag = " <span style='color:#f59e0b;'>⚡ OVERLAP</span>" if u.get("has_overlap") else ""
                            st.markdown(
                                f"""
                                <div class="transcript-card">
                                    <span class="{badge}">{spk}</span>{ov_tag}
                                    <span style="font-size:0.75rem; color:#9ca3af; float:right;">{u.get('start_time')}s - {u.get('end_time')}s</span>
                                    <p style="margin-top:6px; font-size:0.95rem;">{u.get('text')}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.info("Listening for speech... Audio frames stream automatically as speakers talk.")
                except Exception as ex:
                    st.warning(f"Connecting to Gateway... ({ex})")
        else:
            st.info("Click '🟢 Start Online Meeting' above to launch the Google Meet-style split screen view.")

    # RIGHT HALF (50%): TOPIC SEGMENTATION & LLM SUMMARIES
    with right_col:
        st.markdown("### 📌 Topic Segments & LLM Summaries")
        if st.session_state["live_meeting_active"] and st.session_state["live_session_id"]:
            sid = st.session_state["live_session_id"]
            s_data = requests.get(f"{BACKEND_URL}/api/v1/sessions/{sid}").json()
            summary = s_data.get("summary")

            if summary:
                for chapter_title, chunk_summary in summary_cards(summary):
                    st.markdown(
                        f"""
                        <div class="summary-box">
                            <h4 style="margin:0 0 8px 0; color:#c084fc;">📖 {chapter_title}</h4>
                            <p style="margin:0; font-size:0.9rem; white-space:pre-line;">{chunk_summary}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    """
                    <div style="background-color:#1e293b; padding:20px; border-radius:8px; text-align:center;">
                        <h4>Waiting for Topic Segment...</h4>
                        <p style="color:#94a3b8; font-size:0.85rem;">Multiscale TextTiling & ViT5/BARTpho summaries will update here dynamically as meeting topics transition.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Topic summaries and chapter titles from llms-module will display here during live sessions.")


# -----------------------------------------------------------------------------
# TAB 3: MEETING HISTORY
# -----------------------------------------------------------------------------
with nav_history:
    st.markdown("### 📜 Meeting History Archive")
    st.caption("Archived offline and online meetings.")

    if st.button("🔄 Refresh Meeting List", key="hist_refresh"):
        st.rerun()

    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/sessions", timeout=10.0)
        if res.status_code == 200:
            sessions = res.json().get("sessions", [])
            if not sessions:
                st.info("No past meetings found. Upload an audio file or start a live meeting to begin!")
            else:
                for s in sessions:
                    icon = "📁" if s.get("meeting_type") == "offline_upload" else "📹"
                    with st.expander(f"{icon} {s.get('title')} ({s.get('created_at')}) - Status: {s.get('status').upper()}"):
                        st.write(f"**Session ID:** `{s.get('session_id')}`")
                        st.write(f"**Source:** {s.get('audio_source')}")
                        st.write(f"**Meeting Type:** {s.get('meeting_type')}")

                        if st.button("View Transcripts & Summary", key=f"btn_{s.get('session_id')}"):
                            det = requests.get(f"{BACKEND_URL}/api/v1/sessions/{s.get('session_id')}").json()
                            st.json(det)
    except Exception as e:
        st.error(f"Failed to load history: {e}")

# Live Stream Auto-Refresh loop
if st.session_state.get("live_meeting_active", False):
    time.sleep(0.5)
    st.rerun()
