import React, { useEffect, useRef } from 'react';

export default function MainContent({ activeTab, utterances, summary }) {
  const showTranscript = activeTab === 'transcript' || activeTab === 'split';
  const showRecap = activeTab === 'recap' || activeTab === 'split';

  const transcriptBodyRef = useRef(null);
  const prevCountRef = useRef(0);

  // Ensure chronological order with latest message naturally at the bottom
  const sortedUtterances = utterances
    ? [...utterances].sort((a, b) => (a.utterance_index ?? 0) - (b.utterance_index ?? 0))
    : [];

  // When a new message arrives, ensure the viewport shows the latest message at the bottom
  useEffect(() => {
    const currentCount = sortedUtterances.length;
    if (currentCount > prevCountRef.current && transcriptBodyRef.current) {
      transcriptBodyRef.current.scrollTop = transcriptBodyRef.current.scrollHeight;
    }
    prevCountRef.current = currentCount;
  }, [sortedUtterances.length]);

  return (
    <main className="content-area">
      {showTranscript && (
        <div className="split-pane">
          <div className="pane-header">TRANSCRIPT</div>
          <div className="pane-body" ref={transcriptBodyRef}>
            {sortedUtterances && sortedUtterances.length > 0 ? (
              sortedUtterances.map((u, idx) => (
                <div key={u.utterance_id || idx} className="utterance-card">
                  <div className="utterance-meta">
                    <span className="speaker-tag">{u.speaker_id || 'SPK_001'}</span>
                    <span className="timestamp">
                      {u.start_time ? `${u.start_time}s - ${u.end_time}s` : ''}
                    </span>
                  </div>
                  <p className="utterance-text">{u.text}</p>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <h4>No transcript available</h4>
                <p>
                  Press the Record button in the control bar below to begin transcribing speech in
                  real time.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {showRecap && (
        <div className="split-pane">
          <div className="pane-header">AI RECAP & NOTES</div>
          <div className="pane-body">
            {summary && summary.segments && summary.segments.length > 0 ? (
              summary.segments.map((seg, idx) => (
                <div key={idx} className="recap-chapter">
                  <h4 className="recap-title">📖 {seg.title || `Topic Segment ${idx + 1}`}</h4>
                  <p className="recap-text">
                    {seg.chunks ? seg.chunks.map(c => c.rolling_summary).join(' ') : (seg.chunk_summary || '')}
                  </p>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <h4>No Recap Available</h4>
                <p>
                  Recap notes, decisions, and action items will be automatically generated during
                  the session.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
