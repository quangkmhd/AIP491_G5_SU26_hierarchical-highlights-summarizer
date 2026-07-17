import React from 'react';
import { Play, Square, Pause } from 'lucide-react';

interface FloatingControlsProps {
  isRecording: boolean;
  isPaused: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  duration: number; // in seconds
  audioLevels: number[]; // Array of 8 float numbers representing audio frequency/volume levels
}

export const FloatingControls: React.FC<FloatingControlsProps> = ({
  isRecording,
  isPaused,
  onStart,
  onPause,
  onResume,
  onStop,
  duration,
  audioLevels
}) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-30 transition-all duration-300">
      <div className="bg-white/95 border border-slate-200/80 backdrop-blur-md shadow-2xl rounded-full px-6 py-3 flex items-center gap-6 w-auto min-w-[340px] max-w-[480px]">
        
        {/* 1. Real-time Audio Wave Visualizer (Left) */}
        <div className="flex items-center gap-0.5 h-6 w-20 justify-center">
          {audioLevels.map((level, i) => {
            // Compute animated height based on level (min height 3px, max height 24px)
            const height = Math.max(3, level * 24);
            return (
              <div
                key={i}
                style={{ height: `${height}px` }}
                className={`w-[3px] rounded-full transition-all duration-75 ${
                  isRecording && !isPaused ? 'bg-red-500' : 'bg-slate-300'
                }`}
              />
            );
          })}
        </div>

        {/* 2. Timer Counter (Center) */}
        <div className="text-sm font-mono font-semibold text-slate-700 select-none">
          {formatTime(duration)}
        </div>

        {/* Vertical divider */}
        <div className="h-5 w-[1px] bg-slate-200" />

        {/* 3. Button Controls (Right) */}
        <div className="flex items-center gap-3">
          {isRecording ? (
            <>
              {/* Pause/Resume button */}
              {isPaused ? (
                <button
                  onClick={onResume}
                  className="w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center transition-all cursor-pointer"
                  title="Resume Session"
                >
                  <Play className="w-4 h-4 fill-slate-600 text-slate-600" />
                </button>
              ) : (
                <button
                  onClick={onPause}
                  className="w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center transition-all cursor-pointer animate-pulse"
                  title="Pause Session"
                >
                  <Pause className="w-4 h-4 text-slate-600" />
                </button>
              )}

              {/* Stop button */}
              <button
                onClick={onStop}
                className="w-9 h-9 rounded-full bg-red-50 hover:bg-red-100 border border-red-200/50 text-red-500 flex items-center justify-center transition-all cursor-pointer shadow-sm hover:scale-105"
                title="Stop & Save Session"
              >
                <Square className="w-4 h-4 fill-red-500 text-red-500" />
              </button>
            </>
          ) : (
            /* Start Record button */
            <button
              onClick={onStart}
              className="px-5 py-1.5 rounded-full bg-red-500 hover:bg-red-600 text-white font-medium text-xs flex items-center gap-1.5 transition-all shadow-md shadow-red-200 hover:scale-105 cursor-pointer"
              title="Start Recording"
            >
              <div className="w-2.5 h-2.5 bg-white rounded-full animate-ping" />
              Record
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
