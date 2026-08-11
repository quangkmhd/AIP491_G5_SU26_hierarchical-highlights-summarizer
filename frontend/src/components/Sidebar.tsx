import React, { useState } from 'react';
import { 
  Home, 
  Calendar, 
  Settings as SettingsIcon, 
  Info, 
  PenTool, 
  ChevronRight, 
  ChevronLeft, 
  Search, 
  Trash2, 
  Pencil, 
  Check, 
  X
} from 'lucide-react';
import type { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onNewSession: () => void;
  isRecording: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  onNewSession,
  isRecording
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  const filteredSessions = sessions.filter(session => 
    session.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const startRename = (session: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const saveRename = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingSessionId(null);
  };

  const cancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(null);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}s`;
  };

  return (
    <div className="flex h-screen select-none z-20">
      {/* 1. Collapsed/Slim Vertical Icon Navigation Bar (Leftmost) */}
      <div className="w-16 bg-white border-r border-slate-200 flex flex-col items-center py-4 justify-between">
        <div className="flex flex-col items-center gap-6 w-full">
          {/* Logo Icon */}
          <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center cursor-pointer hover:bg-red-100 transition-colors" onClick={onNewSession} title="New Session">
            <div className="relative">
              <PenTool className="w-5 h-5 text-red-500 transform -rotate-45" />
              <div className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-ping" />
            </div>
          </div>
          
          <div className="w-8 border-b border-slate-100 my-2" />

          {/* Navigation Icons */}
          <button className="p-2.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all" title="Home" onClick={onNewSession}>
            <Home className="w-5 h-5" />
          </button>
          
          <button 
            className={`p-2.5 rounded-lg transition-all relative ${isRecording ? 'text-red-500 bg-red-50' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'}`} 
            title={isRecording ? "Recording Active" : "Start Recording"}
          >
            <div className={`w-5 h-5 rounded-full border-2 border-current flex items-center justify-center ${isRecording ? 'animate-pulse' : ''}`}>
              <div className={`w-2.5 h-2.5 rounded-full ${isRecording ? 'bg-red-500 rounded-sm' : 'bg-slate-400'}`} />
            </div>
          </button>

          <button className="p-2.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all" title="Calendar">
            <Calendar className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-col items-center gap-4 w-full">
          <button 
            className="p-2.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all" 
            title="Settings"
            onClick={() => setShowSettingsModal(true)}
          >
            <SettingsIcon className="w-5 h-5" />
          </button>
          
          <button className="p-2.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all" title="About / Info">
            <Info className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 2. Expanded Sidebar - List of Meetings (Slides out/in) */}
      <div 
        className={`bg-slate-50 border-r border-slate-200 flex flex-col transition-all duration-300 relative ${
          isExpanded ? 'w-64' : 'w-0 overflow-hidden border-r-0'
        }`}
      >
        {/* Header inside Panel */}
        <div className="p-4 border-b border-slate-200/80 flex items-center justify-end">
          {/* Collapse Button inside Panel */}
          <button 
            onClick={() => setIsExpanded(false)} 
            className="p-1 rounded-md hover:bg-slate-200 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>

        {/* Search */}
        <div className="p-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search meetings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 bg-white border border-slate-200 rounded-lg text-xs focus:outline-none focus:border-red-500 transition-all"
            />
          </div>
        </div>

        {/* Meetings List */}
        <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-4">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 px-1">Today</div>
            <div className="space-y-1">
              {filteredSessions.map(session => {
                const isActive = session.id === activeSessionId;
                return (
                  <div
                    key={session.id}
                    onClick={() => onSelectSession(session.id)}
                    className={`group p-3 rounded-xl cursor-pointer transition-all flex flex-col gap-1.5 ${
                      isActive 
                        ? 'bg-white shadow-sm border border-slate-200/60 ring-1 ring-slate-100' 
                        : 'hover:bg-slate-200/50 border border-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      {editingSessionId === session.id ? (
                        <div className="flex items-center gap-1 w-full" onClick={e => e.stopPropagation()}>
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="w-full bg-slate-100 border border-slate-300 rounded px-1.5 py-0.5 text-xs font-medium focus:outline-none focus:border-red-500"
                            autoFocus
                          />
                          <button onClick={(e) => saveRename(session.id, e)} className="p-0.5 hover:bg-slate-200 rounded text-green-600">
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={cancelRename} className="p-0.5 hover:bg-slate-200 rounded text-red-500">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span className={`text-xs font-semibold truncate ${isActive ? 'text-slate-800' : 'text-slate-600'}`}>
                          {session.title}
                        </span>
                      )}
                      
                      {editingSessionId !== session.id && (
                        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
                          <button 
                            onClick={(e) => startRename(session, e)} 
                            className="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600"
                            title="Rename"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id); }} 
                            className="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-red-500"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>{session.timestamp}</span>
                      <span>{formatDuration(session.duration)}</span>
                    </div>
                  </div>
                );
              })}
              
              {filteredSessions.length === 0 && (
                <div className="text-center py-6 text-xs text-slate-400 italic">No meetings found</div>
              )}
            </div>
          </div>
        </div>

        {/* Floating Quick Action */}
        <div className="p-3 border-t border-slate-200 bg-slate-50">
          <button 
            onClick={onNewSession}
            disabled={isRecording}
            className="w-full py-2 bg-red-500 hover:bg-red-600 disabled:bg-slate-300 text-white rounded-xl text-xs font-medium transition-colors shadow-sm shadow-red-200 flex items-center justify-center gap-1.5"
          >
            <span>+</span> New Recording
          </button>
        </div>
      </div>

      {/* 3. Floating Expand Button when Sidebar is Collapsed */}
      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          className="absolute left-16 top-4 z-30 p-1.5 rounded-full bg-white border border-slate-200 shadow-md hover:bg-slate-50 hover:scale-105 transition-all text-slate-500"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      )}

      {/* Settings Modal (Radix style overlay) */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden border border-slate-100">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <span className="font-semibold text-slate-800 flex items-center gap-2">
                <SettingsIcon className="w-5 h-5 text-slate-500" /> Settings
              </span>
              <button 
                onClick={() => setShowSettingsModal(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-5 space-y-3 text-sm text-slate-700">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="font-semibold">Accuracy-first</div>
                <div className="mt-1 text-xs text-slate-500">Ưu tiên độ chính xác cho phòng họp 1–3 mét.</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="font-semibold">Microphone DSP</div>
                <div className="mt-1 text-xs text-slate-500">Echo cancellation, noise suppression và auto gain.</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="font-semibold">ASR model</div>
                <div className="mt-1 text-xs text-slate-500">Zipformer-SSL-100h, xử lý câu hoàn chỉnh.</div>
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-end">
              <button 
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-2 bg-slate-800 text-white rounded-xl text-xs font-medium hover:bg-slate-900 transition-colors shadow-sm"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
