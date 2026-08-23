import React, { useState } from 'react';
import { Plus, Search, ChevronLeft, ChevronRight, Trash2, Edit3 } from 'lucide-react';

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateNewSession,
  onDeleteSession,
  onRenameSession,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSessions = sessions.filter((s) =>
    (s.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`} style={collapsed ? { width: '48px', minWidth: '48px' } : {}}>
      <div className="sidebar-header">
        {!collapsed && <span>Meeting Sessions</span>}
        <button
          className="collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {!collapsed && (
        <>
          <div className="sidebar-action-bar">
            <button className="btn-new-session" onClick={onCreateNewSession}>
              <Plus size={16} />
              <span>New Meeting Session</span>
            </button>
          </div>

          <div className="sidebar-search">
            <input
              type="text"
              className="search-input"
              placeholder="Search meetings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="session-list">
            {filteredSessions.map((session) => {
              const isActive = session.session_id === activeSessionId;
              const dateStr = session.created_at
                ? new Date(session.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '04:13';

              return (
                <div
                  key={session.session_id}
                  className={`session-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectSession(session.session_id)}
                >
                  <div className="session-item-header">
                    <span className="session-title" title={session.title}>
                      {session.title || 'Untitled Session'}
                    </span>
                    <div className="session-actions" onClick={(e) => e.stopPropagation()}>
                      <span
                        className="action-link"
                        onClick={() => {
                          const newName = window.prompt('Enter new session title:', session.title);
                          if (newName && newName.trim() && newName.trim() !== session.title) {
                            onRenameSession(session.session_id, newName.trim());
                          }
                        }}
                      >
                        Rename
                      </span>
                      <span
                        className="action-link del"
                        onClick={() => onDeleteSession(session.session_id)}
                      >
                        Del
                      </span>
                    </div>
                  </div>
                  <div className="session-meta">
                    <span>{dateStr} 12-08</span>
                    <span>0:00</span>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </aside>
  );
}
