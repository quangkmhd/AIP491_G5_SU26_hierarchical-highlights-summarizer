import React from 'react';
import { Mic, Square } from 'lucide-react';

export default function ControlBar({
  isRecording,
  recordingTime,
  onToggleRecord,
}) {
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <footer className="control-bar">
      <div className="control-left">
        <div className="wave-dots">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className={`wave-dot ${isRecording ? 'active' : ''}`} />
          ))}
        </div>
      </div>

      <div className="control-center">
        <div className="timer-display">{formatTime(recordingTime)}</div>
        <div className="timer-status">{isRecording ? 'RECORDING...' : 'READY'}</div>
      </div>

      <div className="control-right">
        <button
          className={`btn-record ${isRecording ? 'recording' : ''}`}
          onClick={onToggleRecord}
        >
          {isRecording ? (
            <>
              <Square size={14} fill="currentColor" />
              <span>Stop</span>
            </>
          ) : (
            <>
              <span>Record</span>
            </>
          )}
        </button>
      </div>
    </footer>
  );
}
