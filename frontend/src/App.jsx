import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import NavigationTabs from './components/NavigationTabs';
import MainContent from './components/MainContent';
import ControlBar from './components/ControlBar';
import NewSessionModal from './components/NewSessionModal';
import { useWebSocketAudio } from './hooks/useWebSocketAudio';
import {
  fetchSessions,
  createSession,
  getSessionDetails,
  deleteSession,
  renameSession,
} from './services/api';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [utterances, setUtterances] = useState([]);
  const [summary, setSummary] = useState(null);
  const [activeTab, setActiveTab] = useState('split');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Real-time WebSocket Utterance & Summary Callbacks
  const handleUtteranceReceived = useCallback((newUtterance) => {
    setUtterances((prev) => {
      // Prevent duplicates
      if (prev.some((u) => u.utterance_id === newUtterance.utterance_id)) {
        return prev;
      }
      return [...prev, newUtterance];
    });
  }, []);

  const handleSummaryReceived = useCallback((newSummary) => {
    setSummary(newSummary);
  }, []);

  const { isRecording, recordingTime, startRecording, stopRecording } =
    useWebSocketAudio(activeSessionId, handleUtteranceReceived, handleSummaryReceived);

  // 1. Initial Load: Fetch Sessions
  const loadSessions = async () => {
    const list = await fetchSessions();
    setSessions(list);
    if (list.length > 0 && !activeSessionId) {
      setActiveSessionId(list[0].session_id);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  // 2. Poll Active Session Details periodically for persistence sync
  useEffect(() => {
    if (!activeSessionId) return;

    const fetchDetails = async () => {
      const details = await getSessionDetails(activeSessionId);
      if (details) {
        setActiveSession(details.session);
        setUtterances(details.utterances || []);
        setSummary(details.summary || null);
      }
    };

    fetchDetails();
    const interval = setInterval(fetchDetails, 3000);
    return () => clearInterval(interval);
  }, [activeSessionId]);

  // Handle + New Session Creation with Custom Name from Modal
  const handleCreateSessionWithName = async (customTitle) => {
    try {
      const created = await createSession(customTitle, 'online_live');
      if (created) {
        setSessions((prev) => [created, ...prev]);
        setActiveSessionId(created.session_id);
        setUtterances([]);
        setSummary(null);
      }
    } catch (e) {
      alert('Failed to create new session');
    }
  };

  // Toggle Record / Stop
  const handleToggleRecord = () => {
    if (isRecording) {
      stopRecording();
    } else {
      if (!activeSessionId) {
        setIsModalOpen(true);
      } else {
        startRecording();
      }
    }
  };

  // Copy Transcript to Clipboard
  const handleCopyTranscript = () => {
    if (!utterances || utterances.length === 0) {
      alert('No transcript content to copy.');
      return;
    }
    const textToCopy = utterances
      .map((u) => `[${u.speaker_id || 'SPK'}] ${u.text}`)
      .join('\n');
    navigator.clipboard.writeText(textToCopy);
    alert('Transcript copied to clipboard!');
  };

  // Clear Current Session
  const handleClearSession = () => {
    setUtterances([]);
    setSummary(null);
  };

  // Delete Session
  const handleDeleteSession = async (sid) => {
    if (!window.confirm('Are you sure you want to delete this meeting session?')) {
      return;
    }
    try {
      await deleteSession(sid);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.session_id !== sid);
        if (activeSessionId === sid) {
          if (remaining.length > 0) {
            setActiveSessionId(remaining[0].session_id);
          } else {
            setActiveSessionId(null);
            setActiveSession(null);
            setUtterances([]);
            setSummary(null);
          }
        }
        return remaining;
      });
    } catch (e) {
      alert('Failed to delete session: ' + e.message);
    }
  };

  // Rename Session
  const handleRenameSession = async (sid, newTitle) => {
    try {
      await renameSession(sid, newTitle);
      setSessions((prev) =>
        prev.map((s) => (s.session_id === sid ? { ...s, title: newTitle } : s))
      );
      if (activeSessionId === sid) {
        setActiveSession((prev) => (prev ? { ...prev, title: newTitle } : prev));
      }
    } catch (e) {
      alert('Failed to rename session: ' + e.message);
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onCreateNewSession={() => setIsModalOpen(true)}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
      />

      <div className="main-wrapper">
        <Header
          sessionTitle={activeSession?.title}
          isRecording={isRecording}
          onCopyTranscript={handleCopyTranscript}
          onClearSession={handleClearSession}
        />

        <NavigationTabs activeTab={activeTab} onTabChange={setActiveTab} />

        <MainContent
          activeTab={activeTab}
          utterances={utterances}
          summary={summary}
        />

        <ControlBar
          isRecording={isRecording}
          recordingTime={recordingTime}
          onToggleRecord={handleToggleRecord}
        />
      </div>

      <NewSessionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreateSession={handleCreateSessionWithName}
      />
    </div>
  );
}
