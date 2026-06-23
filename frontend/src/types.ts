export type SummaryMethod = "highlights" | "hierarchical" | "both";
export type ConcreteSummaryMethod = Exclude<SummaryMethod, "both">;

export interface SummaryResponse {
  input_name: string;
  method: SummaryMethod;
  utterance_count: number;
  model_targets: Array<Record<string, string>>;
  langfuse_enabled: boolean;
  langfuse_trace_id: string;
  langfuse_observation_id: string;
  results: {
    highlights?: HighlightsResult;
    hierarchical?: HierarchicalResult;
  };
}

export interface HighlightsResult {
  method: "highlights";
  notes: HighlightItem[];
  tasks: HighlightItem[];
  model_runs: ModelRun[];
}

export interface HighlightItem {
  summary: string;
  source_utterance_id?: number;
  assignee?: string;
  due?: string;
  rewritten_by?: string;
  context?: Utterance[];
}

export interface HierarchicalResult {
  method: "hierarchical";
  chapters: Chapter[];
  model_runs: ModelRun[];
}

export interface Chapter {
  chapter_number: number;
  title: string;
  summary: string;
  timespan: string;
  utterance_ids: number[];
  chunks: Chunk[];
}

export interface Chunk {
  chunk_id: string;
  utterance_ids: number[];
  utterances: Utterance[];
  notes: ChunkNote[];
}

export interface ChunkNote {
  summary: string;
  generated_by?: string;
}

export interface Utterance {
  id: number;
  speaker: string;
  text: string;
}

export interface ModelRun {
  task: string;
  target: string;
  model?: string;
  error?: string;
  attempts?: number;
  duration_seconds?: number;
  raw_preview?: string;
  langfuse_trace_id?: string;
  langfuse_observation_id?: string;
}

export type SummaryStreamEvent =
  | { event: "started"; data: SummaryResponse }
  | { event: "method_started"; data: { method: ConcreteSummaryMethod } }
  | {
      event: "method_completed";
      data:
        | { method: "highlights"; result: HighlightsResult }
        | { method: "hierarchical"; result: HierarchicalResult };
    }
  | { event: "completed"; data: SummaryResponse }
  | { event: "error"; data: { detail: string } };
