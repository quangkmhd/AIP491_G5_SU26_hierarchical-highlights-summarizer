import { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { TranscriptPanel } from './components/TranscriptPanel';
import { FloatingControls } from './components/FloatingControls';
import type { Session, Settings } from './types';

export default function App() {
  const [sessions, setSessions] = useState<Session[]>(() => {
    const saved = localStorage.getItem('vietasr_sessions');
    return saved ? JSON.parse(saved) : [];
  });
  
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    const saved = localStorage.getItem('vietasr_active_id');
    return saved || null;
  });

  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioLevels, setAudioLevels] = useState<number[]>(Array(8).fill(0.1));

  const [settings, setSettings] = useState<Settings>({
    vadThreshold: 0.5,
    provider: 'cuda',
    numThreads: 4,
    captureTabAudio: false
  });

  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(() => {
    return localStorage.getItem('vietasr_selected_device_id') || '';
  });

  // Refs for managing WebSocket and Audio
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const displayStreamRef = useRef<MediaStream | null>(null);

  // Sync refs to avoid stale closures in event handlers.
  // useLayoutEffect fires synchronously after React commits DOM, before browser
  // paint — so refs reflect the latest state before any paint-frame callback.
  const isPausedRef = useRef(isPaused);
  const durationRef = useRef(duration);
  const activeSessionIdRef = useRef(activeSessionId);
  const sessionsRef = useRef(sessions);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  useEffect(() => {
    durationRef.current = duration;
  }, [duration]);

  useLayoutEffect(() => {
    activeSessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  useLayoutEffect(() => {
    sessionsRef.current = sessions;
  }, [sessions]);

  // Persist sessions to LocalStorage
  useEffect(() => {
    localStorage.setItem('vietasr_sessions', JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem('vietasr_active_id', activeSessionId);
    } else {
      localStorage.removeItem('vietasr_active_id');
    }
  }, [activeSessionId]);

  useEffect(() => {
    localStorage.setItem('vietasr_selected_device_id', selectedDeviceId);
  }, [selectedDeviceId]);

  const updateDevices = async () => {
    try {
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = allDevices.filter(d => d.kind === 'audioinput');
      setDevices(audioInputs);
      if (audioInputs.length > 0) {
        const savedId = localStorage.getItem('vietasr_selected_device_id') || '';
        const exists = audioInputs.some(d => d.deviceId === savedId);
        if (!savedId || !exists) {
          const defaultDevice = audioInputs.find(d => d.deviceId === 'default') || audioInputs[0];
          setSelectedDeviceId(defaultDevice.deviceId);
        }
      }
    } catch (err) {
      console.error('Error enumerating audio input devices:', err);
    }
  };

  useEffect(() => {
    // Populate devices on load
    updateDevices();
    
    navigator.mediaDevices.addEventListener('devicechange', updateDevices);
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', updateDevices);
    };
  }, []);

  // Timer effect
  useEffect(() => {
    let interval: any = null;
    if (isRecording && !isPaused) {
      interval = setInterval(() => {
        setDuration(prev => {
          const next = prev + 1;
          // Sync duration back to the active session
          setSessions(prevSessions => prevSessions.map(s => {
            if (s.id === activeSessionIdRef.current) {
              return { ...s, duration: next };
            }
            return s;
          }));
          return next;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording, isPaused]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  const handleNewSession = () => {
    if (isRecording) return;
    const newId = Date.now().toString();
    const newSession: Session = {
      id: newId,
      title: `VietASR Session - ${new Date().toLocaleDateString('vi-VN')} ${new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})}`,
      timestamp: `${new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})} ${new Date().toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit'})}`,
      duration: 0,
      segments: [],
      summary: null,
      recapSegments: [],
      recapChunks: [],
      recapTitles: [],
      hierarchicalRecap: null,
    };

    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newId);
    setDuration(0);
  };

  const handleSelectSession = (id: string) => {
    if (isRecording) {
      alert('Vui lòng dừng phiên ghi âm hiện tại trước khi chuyển sang phiên khác!');
      return;
    }
    setActiveSessionId(id);
    const session = sessions.find(s => s.id === id);
    if (session) {
      setDuration(session.duration);
    }
  };

  const handleDeleteSession = (id: string) => {
    if (isRecording && id === activeSessionId) {
      alert('Không thể xóa phiên đang ghi âm!');
      return;
    }
    
    setSessions(prev => prev.filter(s => s.id !== id));
    
    if (activeSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      if (remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
        setDuration(remaining[0].duration);
      } else {
        setActiveSessionId(null);
        setDuration(0);
      }
    }
  };

  const handleRenameSession = (id: string, newTitle: string) => {
    setSessions(prev => prev.map(s => {
      if (s.id === id) {
        return { ...s, title: newTitle };
      }
      return s;
    }));
  };

  const handleSaveSummary = (summaryText: string) => {
    setSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        return { ...s, summary: summaryText };
      }
      return s;
    }));
  };

  const handleClearSession = () => {
    if (isRecording) {
      alert('Vui lòng dừng ghi âm trước khi xóa dữ liệu của phiên!');
      return;
    }
    setSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        return { ...s, segments: [], summary: null, duration: 0, recapSegments: [], recapChunks: [], recapTitles: [], hierarchicalRecap: null };
      }
      return s;
    }));
    setDuration(0);
  };

  // ---- Session management helpers ----

  const ensureActiveSession = () => {
    // Ensure an empty session exists BEFORE we connect the WebSocket.
    // By the time the first onmessage fires, activeSessionId is already
    // committed to React state and activeSessionIdRef is synced — no race.
    let id = activeSessionIdRef.current;
    const currentActive = sessionsRef.current.find(s => s.id === id) ?? null;
    if (!id || (currentActive && currentActive.segments.length > 0)) {
      id = Date.now().toString();
      const newSession: Session = {
        id,
        title: `VietASR Session - ${new Date().toLocaleDateString('vi-VN')} ${new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})}`,
        timestamp: `${new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})} ${new Date().toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit'})}`,
        duration: 0,
        segments: [],
        summary: null,
        recapSegments: [],
        recapChunks: [],
        recapTitles: [],
        hierarchicalRecap: null,
      };
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(id);
      activeSessionIdRef.current = id;  // immediate sync (complementary to useLayoutEffect)
    }
  };

  // ---- Recording lifecycle ----

  const handleStartRecording = async () => {
    if (isRecording) {
      console.log('[DEBUG] handleStartRecording: already recording, ignore.');
      return;
    }
    console.log('[DEBUG] handleStartRecording triggered.');

    try {
      // 1. Create or reuse session BEFORE opening the socket.
      //    This guarantees the session id exists in state + ref when the first
      //    utterance message arrives.
      ensureActiveSession();
      setDuration(0);
      console.log('[DEBUG] Session ensured. Active ID:', activeSessionIdRef.current);

      // 2. Open microphone stream
      console.log('[DEBUG] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : true 
      });
      mediaStreamRef.current = stream;
      console.log('[DEBUG] Microphone access granted. Stream acquired:', stream.id);

      // 2b. Optionally open display/tab audio stream
      let displayStream: MediaStream | null = null;
      if (settings.captureTabAudio) {
        console.log('[DEBUG] Requesting display/tab audio access...');
        try {
          displayStream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              displaySurface: "monitor" // Gợi ý lấy toàn màn hình để lấy âm thanh hệ thống (loa)
            },
            audio: {
              echoCancellation: false,
              noiseSuppression: false,
              suppressLocalAudioPlayback: false
            },
            systemAudio: "include", // Yêu cầu rõ ràng lấy âm thanh hệ thống (loa)
            surfaceSwitching: "include"
          } as any);
          displayStreamRef.current = displayStream;
          console.log('[DEBUG] Display/tab audio access granted. Stream acquired:', displayStream.id);
        } catch (e) {
          console.warn('[DEBUG] Failed or cancelled display media capture:', e);
        }
      }
      
      // Update device labels now that we have permission
      updateDevices();

      // 3. Open WebSocket connection
      // If we are running on Vite dev server (port 5173), point WebSocket to backend port 8088
      const socketHost = window.location.port === '5173' 
        ? `${window.location.hostname}:8000` 
        : window.location.host;
      const socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${socketHost}/ws`;
      console.log(`[DEBUG] Connecting to WebSocket URL: ${socketUrl}`);
      const clientWs = new WebSocket(socketUrl);
      wsRef.current = clientWs;

      clientWs.onopen = () => {
        console.log('[DEBUG] WebSocket connection established successfully!');
        setIsRecording(true);
        setIsPaused(false);
        console.log('[DEBUG] Calling startAudioProcessing...');
        startAudioProcessing(stream, displayStreamRef.current);
      };

      clientWs.onmessage = (event) => {
        console.log('[DEBUG] WebSocket message received:', event.data);
        try {
          const data = JSON.parse(event.data);

          // Handle utterance events
          if (data.type === 'utterance' && data.text) {
            console.log(`[DEBUG] ASR Segment Received: id=${data.id}, text="${data.text}"`);
            const newSegment = {
              id: data.id,
              text: data.text,
              start_sec: Math.max(0, durationRef.current - (data.duration ?? 0)),
              end_sec: durationRef.current,
              speaker: data.speaker || `Speaker ${String(data.id).padStart(2, '0')}`,
            };
            
            console.log('[DEBUG] Appending segment to session:', activeSessionIdRef.current, newSegment);
            setSessions(prev => prev.map(s => {
              if (s.id === activeSessionIdRef.current) {
                return { ...s, segments: [...s.segments, newSegment] };
              }
              return s;
            }));
            return;
          }

          // Handle recap pipeline events
          if (data.type === 'segment-closed') {
            setSessions(prev => prev.map(s => {
              if (s.id === activeSessionIdRef.current) {
                return { ...s, recapSegments: [...s.recapSegments, {
                  segment_id: data.segment_id,
                  utterances_start: data.utterances_start,
                  utterances_end: data.utterances_end,
                }]};
              }
              return s;
            }));
            return;
          }

          if (data.type === 'chunk-closed') {
            setSessions(prev => prev.map(s => {
              if (s.id === activeSessionIdRef.current) {
                return { ...s, recapChunks: [...s.recapChunks, {
                  chunk_id: data.chunk_id,
                  segment_id: data.segment_id,
                  utterances_start: data.utterances_start,
                  utterances_end: data.utterances_end,
                  rolling_summary: data.rolling_summary,
                }]};
              }
              return s;
            }));
            return;
          }

          if (data.type === 'title-emitted') {
            setSessions(prev => prev.map(s => {
              if (s.id === activeSessionIdRef.current) {
                return { ...s, recapTitles: [...s.recapTitles, {
                  segment_id: data.segment_id,
                  title: data.title,
                }]};
              }
              return s;
            }));
            return;
          }

          if (data.type === 'meeting-completed') {
            setSessions(prev => prev.map(s => {
              if (s.id === activeSessionIdRef.current) {
                return { ...s, hierarchicalRecap: data.hierarchical_recap };
              }
              return s;
            }));
            return;
          }

          console.log('[DEBUG] Ignored WebSocket message (unrecognized type):', data.type);
        } catch (err) {
          console.error('[DEBUG] Failed to parse WebSocket message JSON:', err);
        }
      };

      clientWs.onclose = (event) => {
        console.log('[DEBUG] WebSocket connection closed by server/client. Event:', event);
        handleStopRecording();
      };

      clientWs.onerror = (error) => {
        console.error('[DEBUG] WebSocket connection encountered error:', error);
      };
    } catch (err) {
      console.error('[DEBUG] Failed to start recording / setup websocket:', err);
      alert('Không thể truy cập microphone hoặc kết nối đến ASR Backend. Hãy đảm bảo backend đang chạy ở cổng 8000!');
    }
  };

  const downsampleBuffer = (buffer: Float32Array, fromRate: number, toRate: number): Float32Array => {
    if (fromRate === toRate) return buffer;
    const sampleRateRatio = fromRate / toRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  };

  const startAudioProcessing = (micStream: MediaStream, displayStream: MediaStream | null) => {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    console.log('[DEBUG] Initializing Web Audio Context...');
    const audioCtx = new AudioCtx();
    audioContextRef.current = audioCtx;
    
    // Explicitly resume the AudioContext to prevent modern browsers from suspending it
    if (audioCtx.state === 'suspended') {
      console.log('[DEBUG] AudioContext is suspended. Calling resume()...');
      audioCtx.resume().then(() => {
        console.log('[DEBUG] AudioContext resumed successfully. Sample rate:', audioCtx.sampleRate);
      });
    } else {
      console.log('[DEBUG] AudioContext running. Sample rate:', audioCtx.sampleRate);
    }
    
    // Analyzer for bouncing bars visualizer
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 32; // small fft size is fast
    
    // ScriptProcessor node for capturing raw samples
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;
    
    // Connect microphone
    const micSource = audioCtx.createMediaStreamSource(micStream);
    micSource.connect(analyser);
    micSource.connect(processor);
    console.log('[DEBUG] Microphone connected to Web Audio graph.');
    
    // Connect display audio if available
    if (displayStream) {
      const displayAudioTracks = displayStream.getAudioTracks();
      if (displayAudioTracks.length > 0) {
        console.log('[DEBUG] Found display audio track:', displayAudioTracks[0].label);
        const displayAudioStream = new MediaStream([displayAudioTracks[0]]);
        const displaySource = audioCtx.createMediaStreamSource(displayAudioStream);
        displaySource.connect(analyser);
        displaySource.connect(processor);
        console.log('[DEBUG] Display/tab audio connected to Web Audio graph.');
      } else {
        console.log('[DEBUG] No audio tracks found in display stream.');
      }
    }
    
    processor.connect(audioCtx.destination);
    console.log('[DEBUG] ScriptProcessor connected to output destination.');
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const updateLevels = () => {
      if (!audioContextRef.current || audioCtx.state === 'closed') {
        setAudioLevels(Array(8).fill(0.1));
        return;
      }
      if (isPausedRef.current) {
        setAudioLevels(Array(8).fill(0.1));
        return;
      }
      
      analyser.getByteFrequencyData(dataArray);
      
      // Map visual frequencies to 8 bars
      const levels = [];
      const step = Math.floor(bufferLength / 8) || 1;
      for (let i = 0; i < 8; i++) {
        const val = dataArray[i * step] || 0;
        // Boost mid range frequencies slightly for visual aesthetics
        let valNorm = val / 255.0;
        if (i > 1 && i < 6) valNorm *= 1.4;
        levels.push(Math.min(1.0, Math.max(0.1, valNorm)));
      }
      setAudioLevels(levels);
      requestAnimationFrame(updateLevels);
    };
    
    requestAnimationFrame(updateLevels);
    processor.onaudioprocess = (e) => {
      if (isPausedRef.current) return;
      const inputData = e.inputBuffer.getChannelData(0); // Float32Array at native sample rate
      const resampledData = downsampleBuffer(inputData, audioCtx.sampleRate, 16000);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(resampledData.buffer as any);
      }
    };
  };

  const handlePauseRecording = () => {
    setIsPaused(true);
  };

  const handleResumeRecording = () => {
    setIsPaused(false);
  };

  const handleStopRecording = () => {
    // 1. Close Web Audio nodes
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (displayStreamRef.current) {
      displayStreamRef.current.getTracks().forEach(track => track.stop());
      displayStreamRef.current = null;
    }
    
    // 2. Close socket
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }

    setIsRecording(false);
    setIsPaused(false);
    setAudioLevels(Array(8).fill(0.1));
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100">
      {/* Collapsible/Double Sidebar component */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        onNewSession={handleNewSession}
        settings={settings}
        onUpdateSettings={setSettings}
        isRecording={isRecording}
      />

      {/* Main Workspace component */}
      <TranscriptPanel
        title={activeSession ? activeSession.title : "VietASR Session"}
        onRenameTitle={(newTitle) => activeSessionId && handleRenameSession(activeSessionId, newTitle)}
        segments={activeSession ? activeSession.segments : []}
        isRecording={isRecording}
        isPaused={isPaused}
        onClear={handleClearSession}
        summary={activeSession ? activeSession.summary : null}
        onSaveSummary={handleSaveSummary}
        devices={devices}
        selectedDeviceId={selectedDeviceId}
        onSelectDevice={setSelectedDeviceId}
        recapSegments={activeSession ? activeSession.recapSegments : []}
        recapChunks={activeSession ? activeSession.recapChunks : []}
        recapTitles={activeSession ? activeSession.recapTitles : []}
        hierarchicalRecap={activeSession ? activeSession.hierarchicalRecap : null}
      />

      {/* Floating Pill Controls component */}
      {(isRecording || activeSessionId) && (
        <FloatingControls
          isRecording={isRecording}
          isPaused={isPaused}
          onStart={handleStartRecording}
          onPause={handlePauseRecording}
          onResume={handleResumeRecording}
          onStop={handleStopRecording}
          duration={duration}
          audioLevels={audioLevels}
        />
      )}
    </div>
  );
}
