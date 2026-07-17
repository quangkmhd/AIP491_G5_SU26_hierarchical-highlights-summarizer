export interface TranscriptSegment {
  id: number;
  text: string;
  start_sec: number;
  end_sec: number;
  speaker: string;
  confidence?: number;
}

export interface Session {
  id: string;
  title: string;
  timestamp: string;
  duration: number; // in seconds
  segments: TranscriptSegment[];
  summary: string | null;
  // Recap pipeline data
  recapSegments: RecapSegment[];
  recapChunks: RecapChunk[];
  recapTitles: RecapTitle[];
  hierarchicalRecap: any | null;
}

export interface Settings {
  vadThreshold: number;
  provider: 'cpu' | 'cuda';
  numThreads: number;
  captureTabAudio?: boolean;
}

// --- Recap Pipeline Events ---

export interface RecapSegment {
  segment_id: string;
  utterances_start: number;
  utterances_end: number;
}

export interface RecapChunk {
  chunk_id: string;
  segment_id: string;
  utterances_start: number;
  utterances_end: number;
  rolling_summary: string;
}

export interface RecapTitle {
  segment_id: string;
  title: string;
}
