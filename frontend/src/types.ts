export interface TranscriptSegment {
  id: number;
  text: string;
  start_sec: number;
  end_sec: number;
  speaker: string;
  confidence?: number;
  quality?: {
    rms: number;
    peak: number;
    clipped: boolean;
    vad_confidence: number;
    speech_duration: number;
  };
  degraded?: boolean;
  fallback?: boolean;
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

export interface DemoTimelineItem {
  line_number: number;
  recording_id: string;
  relative_path: string;
  sample_count: number;
  start_sample: number;
  end_sample: number;
  gap_samples: number;
  sha256: string;
}

export interface DemoTimelineManifest {
  schema_version: number;
  sample_rate: 16000;
  duration_samples: number;
  gap_samples: number;
  padding_samples: number;
  recordings_manifest_sha256: string;
  items: DemoTimelineItem[];
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
