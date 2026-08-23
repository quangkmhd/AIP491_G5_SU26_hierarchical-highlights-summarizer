import React from 'react';
import { Copy, Trash2 } from 'lucide-react';

export default function Header({
  sessionTitle,
  isRecording,
  onCopyTranscript,
  onClearSession,
}) {
  return (
    <header className="top-header">
      <div className="header-left">
        <h2 className="meeting-title">{sessionTitle || 'VietASR Session - 12/8/2026 04:13'}</h2>
        <span className={`status-badge ${isRecording ? 'recording' : 'idle'}`}>
          {isRecording ? 'RECORDING' : 'IDLE'}
        </span>
      </div>

      <div className="header-controls">
        <button className="btn-header" onClick={onCopyTranscript} title="Copy transcript to clipboard">
          Copy
        </button>

        <button className="btn-header clear" onClick={onClearSession} title="Clear session content">
          Clear
        </button>
      </div>
    </header>
  );
}
