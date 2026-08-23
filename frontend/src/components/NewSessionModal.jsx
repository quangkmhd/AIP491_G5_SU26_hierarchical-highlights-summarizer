import React, { useState } from 'react';
import { X, Sparkles } from 'lucide-react';

export default function NewSessionModal({ isOpen, onClose, onCreateSession }) {
  const [sessionTitle, setSessionTitle] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const now = new Date();
    const defaultDate = `${now.getDate()}/${now.getMonth() + 1}/${now.getFullYear()} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    const finalTitle = sessionTitle.trim() || `Meeting Session - ${defaultDate}`;
    onCreateSession(finalTitle);
    setSessionTitle('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <Sparkles size={18} className="modal-icon" />
            <h3>Create New Session</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <label htmlFor="session-name-input">Meeting Session Name</label>
            <input
              id="session-name-input"
              type="text"
              className="modal-input"
              placeholder="e.g. Weekly Architecture Review, Q3 Product Sync..."
              value={sessionTitle}
              onChange={(e) => setSessionTitle(e.target.value)}
              autoFocus
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-modal-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-modal-submit">
              Create Session
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
