import React, { useState, useRef, useEffect } from 'react';
import { Copy, Trash2, Layout, FileText, Check, Sparkles, BookOpen, CheckCircle } from 'lucide-react';
import type { TranscriptSegment, RecapSegment, RecapChunk, RecapTitle } from '../types';

interface TranscriptPanelProps {
  title: string;
  onRenameTitle: (newTitle: string) => void;
  segments: TranscriptSegment[];
  isRecording: boolean;
  isPaused: boolean;
  onClear: () => void;
  summary: string | null;
  onSaveSummary: (summary: string) => void;
  devices: MediaDeviceInfo[];
  selectedDeviceId: string;
  onSelectDevice: (deviceId: string) => void;
  recapSegments: RecapSegment[];
  recapChunks: RecapChunk[];
  recapTitles: RecapTitle[];
  hierarchicalRecap: any | null;
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  title,
  onRenameTitle,
  segments,
  isRecording,
  isPaused,
  onClear,
  summary,
  onSaveSummary,
  devices,
  selectedDeviceId,
  onSelectDevice,
  recapSegments: _recapSegments,
  recapChunks,
  recapTitles,
  hierarchicalRecap
}) => {
  const [viewMode, setViewMode] = useState<'split' | 'transcript' | 'summary'>('split');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState(title);
  const [copied, setCopied] = useState(false);
  const [summaryText, setSummaryText] = useState(summary || '');
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEditedTitle(title);
  }, [title]);

  useEffect(() => {
    setSummaryText(summary || '');
  }, [summary]);

  // Auto-scroll to bottom of transcripts
  useEffect(() => {
    if (isRecording) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [segments, isRecording]);

  const handleCopy = () => {
    const fullText = segments
      .map(s => `[${formatTime(s.start_sec)}] ${s.speaker}: ${s.text}`)
      .join('\n');
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleGenerateSummary = () => {
    if (segments.length === 0) return;
    setIsGeneratingSummary(true);
    
    // Simulate summary generation with a detailed prompt and timer
    setTimeout(() => {
      const summaryContent = `# Tóm tắt phiên họp: ${title}

## Tóm tắt nội dung chính
Phiên họp thảo luận về các vấn đề nhận diện giọng nói tiếng Việt thời gian thực (realtime streaming ASR). Người phát biểu đã trình bày về cấu trúc hệ thống, bao gồm VAD (Voice Activity Detector) để lọc khoảng lặng và ASR Engine để chuyển âm thanh thành văn bản.

## Các quyết định quan trọng
*   Sử dụng framework **React (Vite)** phối hợp với **FastAPI** và kết nối qua **WebSocket** để đạt độ trễ thấp nhất.
*   Cài đặt giao diện thu âm nổi (Floating Controls) cùng hiệu ứng sóng âm động nhằm tăng tính tương tác.
*   Lưu lịch sử hội thoại cục bộ qua LocalStorage.

## Kế hoạch hành động
*   [ ] Hoàn thành viết mã nguồn frontend cho các component.
*   [ ] Chạy thử nghiệm kết nối WebSocket để đo đạc độ trễ và RTF (Real-time Factor).
*   [ ] Tối ưu hóa mô hình trên GPU sử dụng CUDA.`;
      
      setSummaryText(summaryContent);
      onSaveSummary(summaryContent);
      setIsGeneratingSummary(false);
      setViewMode('split');
    }, 2000);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex-1 flex flex-col bg-white h-screen overflow-hidden relative">
      {/* 1. Header Area */}
      <div className="px-6 py-4 border-b border-slate-200/80 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white z-10">
        <div className="flex items-center gap-3">
          {isEditingTitle ? (
            <input
              type="text"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              onBlur={() => {
                setIsEditingTitle(false);
                if (editedTitle.trim()) onRenameTitle(editedTitle.trim());
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setIsEditingTitle(false);
                  if (editedTitle.trim()) onRenameTitle(editedTitle.trim());
                }
              }}
              className="text-lg font-bold text-slate-800 border-b border-red-500 focus:outline-none py-0.5 px-1 bg-slate-50 rounded"
              autoFocus
            />
          ) : (
            <h1 
              onClick={() => setIsEditingTitle(true)}
              className="text-lg font-bold text-slate-800 cursor-pointer hover:bg-slate-50 px-1 rounded transition-colors truncate max-w-[320px] md:max-w-[450px]"
              title="Click to rename"
            >
              {title}
            </h1>
          )}
          
          {/* Connection status indicator */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200/50">
            <div className={`w-2 h-2 rounded-full ${isRecording ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              {isRecording ? (isPaused ? 'Paused' : 'Recording') : 'Idle'}
            </span>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2">
          {/* Microphone Selector */}
          {devices.length > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white">
              <span className="text-slate-400 text-xs">🎙️</span>
              <select
                value={selectedDeviceId}
                onChange={(e) => onSelectDevice(e.target.value)}
                disabled={isRecording}
                className="bg-transparent border-0 text-[11px] font-semibold focus:outline-none focus:ring-0 text-slate-600 max-w-[140px] cursor-pointer"
                title="Select Microphone Input"
              >
                {devices.map(device => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Microphone ${device.deviceId.slice(0, 5)}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* View Mode Switcher */}
          <div className="bg-slate-100 p-0.5 rounded-xl border border-slate-200/40 flex items-center">
            <button
              onClick={() => setViewMode('transcript')}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === 'transcript' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'
              }`}
              title="Transcript Only"
            >
              <FileText className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">Transcript</span>
            </button>
            <button
              onClick={() => setViewMode('split')}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === 'split' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'
              }`}
              title="Split Screen"
            >
              <Layout className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">Split View</span>
            </button>
            <button
              onClick={() => setViewMode('summary')}
              className={`p-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === 'summary' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'
              }`}
              title="Recap Only"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">AI Recap</span>
            </button>
          </div>

          <div className="h-6 w-[1px] bg-slate-200 mx-1" />

          {/* Transcript Control buttons */}
          <button
            onClick={handleCopy}
            disabled={segments.length === 0}
            className="p-2 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-800 disabled:text-slate-300 disabled:bg-slate-50 hover:bg-slate-50 font-medium text-xs flex items-center gap-1.5 transition-all"
            title="Copy all transcript"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            onClick={onClear}
            disabled={segments.length === 0 && !summaryText}
            className="p-2 rounded-xl border border-slate-200 text-slate-500 hover:text-red-600 disabled:text-slate-300 disabled:bg-slate-50 hover:bg-red-50 hover:border-red-100 font-medium text-xs flex items-center gap-1.5 transition-all"
            title="Clear current data"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Clear</span>
          </button>
        </div>
      </div>

      {/* 2. Workspace Area */}
      <div className="flex-1 flex overflow-hidden bg-slate-50/50">
        
        {/* LEFT COMPONENT: Transcript View */}
        <div 
          className={`flex-1 flex flex-col h-full bg-white transition-all duration-300 border-r border-slate-100 ${
            viewMode === 'summary' ? 'w-0 overflow-hidden hidden border-r-0' : 'w-full'
          }`}
        >
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
            {segments.map((segment) => (
              <div key={segment.id} className="flex gap-4 items-start group">
                {/* Time Indicator */}
                <div className="text-[11px] font-mono text-slate-400 select-none w-14 mt-1">
                  [{formatTime(segment.start_sec)}]
                </div>
                
                {/* Speech bubble card */}
                <div className="flex-1 bg-white border border-slate-100 p-4 rounded-2xl shadow-sm hover:shadow transition-shadow">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-700">{segment.speaker}</span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-50 border border-slate-100 px-1.5 py-0.5 rounded">
                      {(segment.end_sec - segment.start_sec).toFixed(1)}s
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-700 font-medium">
                    {segment.text}
                  </p>
                </div>
              </div>
            ))}

            {/* Listening Indicator */}
            {isRecording && !isPaused && (
              <div className="flex gap-4 items-center pl-1">
                <div className="w-14" />
                <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                  </span>
                  <span>Listening...</span>
                </div>
              </div>
            )}

            {segments.length === 0 && !isRecording && (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 select-none">
                <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mb-4 text-slate-400 border border-slate-100">
                  🎙️
                </div>
                <h3 className="font-semibold text-slate-800 text-sm mb-1">No speech transcribed</h3>
                <p className="text-xs text-slate-400 max-w-xs">
                  Click the Record button in the control panel below to start transcribing speech from your microphone in real-time.
                </p>
              </div>
            )}
            
            {/* Recap Pipeline Results */}
            {(recapTitles.length > 0 || recapChunks.length > 0) && (
              <div className="mt-6 border-t border-slate-200 pt-4">
                <h3 className="text-lg font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-indigo-500" />
                  Meeting Recap
                </h3>
                
                {recapTitles.map((rt, idx) => {
                  const chunkSummaries = recapChunks.filter(c => c.segment_id === rt.segment_id);
                  return (
                    <div key={rt.segment_id} className="mb-4 rounded-lg bg-indigo-50 border border-indigo-100 p-4">
                      <h4 className="font-semibold text-indigo-700 mb-2">
                        Chapter {idx + 1}: {rt.title}
                      </h4>
                      {chunkSummaries.map(cs => (
                        <p key={cs.chunk_id} className="text-sm text-slate-600 mb-1 pl-3 border-l-2 border-indigo-200">
                          {cs.rolling_summary}
                        </p>
                      ))}
                    </div>
                  );
                })}

                {hierarchicalRecap && (
                  <div className="mt-4 rounded-lg bg-emerald-50 border border-emerald-200 p-4">
                    <h4 className="font-semibold text-emerald-700 mb-2 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Meeting Summary Complete
                    </h4>
                    <p className="text-sm text-emerald-600">
                      {hierarchicalRecap.segments?.length || 0} chapters detected, 
                      processed in {hierarchicalRecap.processing_time_ms}ms
                    </p>
                  </div>
                )}
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* RIGHT COMPONENT: Summary/Notes View */}
        <div 
          className={`flex-1 flex flex-col h-full bg-slate-50/30 transition-all duration-300 ${
            viewMode === 'transcript' ? 'w-0 overflow-hidden hidden' : 'w-full'
          }`}
        >
          <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col h-full">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-500" /> AI recap &amp; notes
              </span>
              
              {segments.length > 0 && !summaryText && !isGeneratingSummary && (
                <button
                  onClick={handleGenerateSummary}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-medium transition-all shadow-sm flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Generate Recap
                </button>
              )}
            </div>

            <div className="flex-1 bg-white border border-slate-200/60 rounded-2xl shadow-sm p-6 flex flex-col">
              {isGeneratingSummary ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                  <div className="w-10 h-10 border-4 border-slate-200 border-t-red-500 rounded-full animate-spin mb-4" />
                  <p className="text-xs text-slate-500 font-medium">Analyzing speech content and generating meeting recap...</p>
                </div>
              ) : summaryText ? (
                <textarea
                  value={summaryText}
                  onChange={(e) => {
                    setSummaryText(e.target.value);
                    onSaveSummary(e.target.value);
                  }}
                  className="w-full flex-1 resize-none border-0 p-0 text-sm focus:outline-none focus:ring-0 leading-relaxed text-slate-700 font-mono"
                  placeholder="Review or edit the meeting summary..."
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 select-none">
                  <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center mb-3 text-slate-400 border border-slate-100">
                    📝
                  </div>
                  <h3 className="font-semibold text-slate-700 text-xs mb-1">No Recap Available</h3>
                  <p className="text-xs text-slate-400 max-w-xs mb-4">
                    Once you have recording segments, click "Generate Recap" to draft structured notes, decisions, and action items.
                  </p>
                  <button
                    onClick={handleGenerateSummary}
                    disabled={segments.length === 0}
                    className="px-4 py-2 bg-slate-50 hover:bg-slate-100 disabled:opacity-50 border border-slate-200 text-slate-600 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-slate-400" /> Draft Recap
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
