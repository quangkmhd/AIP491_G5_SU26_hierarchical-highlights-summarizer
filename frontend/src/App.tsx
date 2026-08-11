import { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { TranscriptPanel } from './components/TranscriptPanel';
import { FloatingControls } from './components/FloatingControls';
import { DemoStatus } from './components/DemoStatus';
import { DemoAudioClient, type DemoProgress } from './audio/demoAudioClient';
import { MeetingAudioClient, type ProcessingState } from './audio/meetingAudioClient';
import type { Session } from './types';

export default function App() {
  const demoMode = new URLSearchParams(window.location.search).get('demo') === 'custom10h';
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
  const [processingState, setProcessingState] = useState<ProcessingState>('idle');
  const [demoProgress, setDemoProgress] = useState<DemoProgress>({
    recordingId: null,
    elapsedSamples: 0,
    totalSamples: 0,
  });
  const [demoError, setDemoError] = useState<string | null>(null);

  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(() => {
    return localStorage.getItem('vietasr_selected_device_id') || '';
  });

  const audioClientRef = useRef<MeetingAudioClient | DemoAudioClient | null>(null);

  useEffect(() => {
    if (!demoMode) return;
    document.body.dataset.demoState = 'idle';
    return () => {
      delete document.body.dataset.demoState;
    };
  }, [demoMode]);

  // Sync refs to avoid stale closures in event handlers.
  // useLayoutEffect fires synchronously after React commits DOM, before browser
  // paint — so refs reflect the latest state before any paint-frame callback.
  const activeSessionIdRef = useRef(activeSessionId);
  const sessionsRef = useRef(sessions);

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
    if (demoMode) return;
    // Populate devices on load
    updateDevices();
    
    navigator.mediaDevices.addEventListener('devicechange', updateDevices);
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', updateDevices);
    };
  }, [demoMode]);

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

  const ensureActiveSession = (forcedTitle?: string) => {
    // Ensure an empty session exists BEFORE we connect the WebSocket.
    // By the time the first onmessage fires, activeSessionId is already
    // committed to React state and activeSessionIdRef is synced — no race.
    let id = activeSessionIdRef.current;
    const currentActive = sessionsRef.current.find(s => s.id === id) ?? null;
    if (forcedTitle || !id || (currentActive && currentActive.segments.length > 0)) {
      id = Date.now().toString();
      const newSession: Session = {
        id,
        title: forcedTitle ?? `VietASR Session - ${new Date().toLocaleDateString('vi-VN')} ${new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'})}`,
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

  const handleServerEvent = (data: Record<string, any>) => {
    if (data.type === 'utterance' && data.text) {
      const newSegment = {
        id: Number(data.id),
        text: String(data.text),
        start_sec: Number(data.start_sec),
        end_sec: Number(data.end_sec),
        speaker: String(data.speaker || 'Unknown Speaker'),
        quality: data.quality,
        degraded: Boolean(data.degraded),
        fallback: Boolean(data.fallback),
      };
      setSessions(prev => prev.map(s => {
        if (s.id !== activeSessionIdRef.current) return s;
        const filtered = s.segments.filter(segment => segment.id !== newSegment.id);
        return { ...s, segments: [...filtered, newSegment] };
      }));
      return;
    }

    if (data.type === 'segment-closed') {
      setSessions(prev => prev.map(s => s.id === activeSessionIdRef.current ? {
        ...s,
        recapSegments: [...s.recapSegments, {
          segment_id: data.segment_id,
          utterances_start: data.utterances_start,
          utterances_end: data.utterances_end,
        }],
      } : s));
      return;
    }
    if (data.type === 'chunk-closed') {
      setSessions(prev => prev.map(s => s.id === activeSessionIdRef.current ? {
        ...s,
        recapChunks: [...s.recapChunks, {
          chunk_id: data.chunk_id,
          segment_id: data.segment_id,
          utterances_start: data.utterances_start,
          utterances_end: data.utterances_end,
          rolling_summary: data.rolling_summary,
        }],
      } : s));
      return;
    }
    if (data.type === 'title-emitted') {
      setSessions(prev => prev.map(s => s.id === activeSessionIdRef.current ? {
        ...s,
        recapTitles: [...s.recapTitles, {
          segment_id: data.segment_id,
          title: data.title,
        }],
      } : s));
      return;
    }
    if (data.type === 'meeting-completed') {
      setSessions(prev => prev.map(s => s.id === activeSessionIdRef.current
        ? { ...s, hierarchicalRecap: data.hierarchical_recap }
        : s));
    }
  };

  const handleStartRecording = async () => {
    if (isRecording || audioClientRef.current) return;
    ensureActiveSession();
    setDuration(0);

    const backendPort = import.meta.env.VITE_BACKEND_PORT || '8005';
    const socketHost = window.location.port === '5173'
      ? `${window.location.hostname}:${backendPort}`
      : window.location.host;
    const socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${socketHost}/ws`;
    const client = new MeetingAudioClient({
      socketUrl,
      deviceId: selectedDeviceId || undefined,
      onEvent: handleServerEvent,
      onLevels: setAudioLevels,
      onState: (state) => {
        setProcessingState(state);
        setIsRecording(['recording', 'paused', 'degraded', 'finalizing'].includes(state));
        setIsPaused(state === 'paused');
      },
      onError: (error) => {
        console.error('Meeting audio pipeline failed:', error);
        alert(`Không thể xử lý âm thanh: ${error.message}`);
      },
    });
    audioClientRef.current = client;

    try {
      await client.start();
      await updateDevices();
    } catch {
      audioClientRef.current = null;
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const handleStartDemo = async () => {
    if (isRecording || audioClientRef.current) return;
    ensureActiveSession('Custom_10h · Real-time 1-hour Demo');
    setDuration(0);
    setDemoError(null);
    setDemoProgress({ recordingId: null, elapsedSamples: 0, totalSamples: 0 });

    const backendPort = import.meta.env.VITE_BACKEND_PORT || '8005';
    const backendHost = window.location.port === '5173'
      ? `${window.location.hostname}:${backendPort}`
      : window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const socketProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const client = new DemoAudioClient({
      apiBaseUrl: `${protocol}//${backendHost}`,
      socketUrl: `${socketProtocol}//${backendHost}/ws`,
      onEvent: handleServerEvent,
      onProgress: setDemoProgress,
      onState: (state) => {
        setProcessingState(state);
        setIsRecording(['recording', 'paused', 'degraded', 'finalizing'].includes(state));
        setIsPaused(state === 'paused');
      },
      onError: (error) => {
        console.error('Demo audio pipeline failed:', error);
        setDemoError(error.message);
      },
    });
    audioClientRef.current = client;
    try {
      await client.start();
    } catch {
      setIsRecording(false);
      setIsPaused(false);
    } finally {
      audioClientRef.current = null;
    }
  };

  const handlePauseRecording = () => { void audioClientRef.current?.pause(); };
  const handleResumeRecording = () => { void audioClientRef.current?.resume(); };

  const handleStopRecording = async () => {
    const client = audioClientRef.current;
    if (!client) return;
    await client.stop(true);
    audioClientRef.current = null;
    setAudioLevels(Array(8).fill(0.1));
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100">
      <DemoStatus
        visible={demoMode}
        state={processingState}
        progress={demoProgress}
        error={demoError}
      />
      {/* Collapsible/Double Sidebar component */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        onNewSession={handleNewSession}
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
        showMicrophoneSelector={!demoMode}
      />

      {/* Floating Pill Controls component */}
      {(isRecording || activeSessionId || demoMode) && (
        <FloatingControls
          isRecording={isRecording}
          isPaused={isPaused}
          onStart={demoMode ? handleStartDemo : handleStartRecording}
          onPause={handlePauseRecording}
          onResume={handleResumeRecording}
          onStop={handleStopRecording}
          duration={duration}
          audioLevels={audioLevels}
          processingState={processingState}
          startLabel={demoMode ? 'Bắt đầu demo' : 'Record'}
        />
      )}
    </div>
  );
}
