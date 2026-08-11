import React from 'react';
import type { DemoProgress } from '../audio/demoAudioClient';
import type { ProcessingState } from '../audio/audioSessionSocket';

interface DemoStatusProps {
  visible: boolean;
  state: ProcessingState;
  progress: DemoProgress;
  error: string | null;
}

export const DemoStatus: React.FC<DemoStatusProps> = ({
  visible,
  state,
  progress,
  error,
}) => {
  if (!visible) return null;
  const percentage = progress.totalSamples > 0
    ? Math.min(100, Math.round(progress.elapsedSamples / progress.totalSamples * 100))
    : 0;

  return (
    <div className="fixed right-6 top-5 z-40 w-80 rounded-2xl border border-red-200 bg-white/95 p-4 shadow-xl backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-bold tracking-wide text-red-600">
          LIVE DEMO · Custom_10h
        </span>
        <span className="text-[10px] font-semibold uppercase text-slate-500">{state}</span>
      </div>
      <div
        className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        data-testid="demo-progress"
        aria-label="Tiến độ demo"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percentage}
      >
        <div className="h-full bg-red-500 transition-all" style={{ width: `${percentage}%` }} />
      </div>
      <div className="mt-2 truncate text-[11px] text-slate-500">
        {progress.recordingId ?? 'Sẵn sàng phát tuần tự'} · {percentage}%
      </div>
      {error && <p className="mt-2 text-xs font-medium text-red-600">{error}</p>}
    </div>
  );
};
