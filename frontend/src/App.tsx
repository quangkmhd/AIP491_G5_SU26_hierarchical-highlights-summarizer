import { FormEvent, useEffect, useMemo, useState } from "react";
import { streamSummaryMeeting } from "./api";
import type {
  Chapter,
  Chunk,
  ConcreteSummaryMethod,
  HighlightItem,
  HighlightsResult,
  HierarchicalResult,
  ModelRun,
  SummaryMethod,
  SummaryResponse,
  SummaryStreamEvent
} from "./types";

const SAMPLE_TRANSCRIPT = `Lan(09:00 - 09:01):
Chúng ta thống nhất kiến trúc summary gồm highlight và hierarchical.
Minh(09:01 - 09:02):
Tuần này cần tạo FastAPI app và frontend để nhập transcript.
Lan(09:02 - 09:03):
Phần hierarchical nên giữ mạch theo chương để dễ đọc lại bối cảnh.
Minh(09:03 - 09:04):
Em sẽ viết test và report kết quả chạy demo.`;

const METHOD_OPTIONS: Array<{ value: SummaryMethod; label: string; kicker: string; body: string }> = [
  {
    value: "highlights",
    label: "Highlights",
    kicker: "DR1",
    body: "Flat notes and action items for quick coordination."
  },
  {
    value: "hierarchical",
    label: "Hierarchical",
    kicker: "DR2",
    body: "Chapterized minutes that preserve discussion flow."
  },
  {
    value: "both",
    label: "Both",
    kicker: "Compare",
    body: "Run both methods and inspect the output shape side by side."
  }
];

export default function App() {
  const [inputName, setInputName] = useState("frontend-input.md");
  const [method, setMethod] = useState<SummaryMethod>("both");
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [runTelemetry, setRunTelemetry] = useState<RunTelemetry>({
    elapsedMs: 0,
    finishedAtLabel: "",
    requestCount: 0,
    startedAtLabel: "",
    status: "idle"
  });

  const transcriptStats = useMemo(() => getTranscriptStats(transcript), [transcript]);
  const outputStats = useMemo(() => getOutputStats(result), [result]);

  useEffect(() => {
    if (runTelemetry.status !== "running" || runTelemetry.startedAtMs === undefined) {
      return;
    }
    const timer = window.setInterval(() => {
      setRunTelemetry((current) => {
        if (current.status !== "running" || current.startedAtMs === undefined) {
          return current;
        }
        return { ...current, elapsedMs: performance.now() - current.startedAtMs };
      });
    }, 250);
    return () => window.clearInterval(timer);
  }, [runTelemetry.status, runTelemetry.startedAtMs]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const startedAtMs = performance.now();
    const startedAtLabel = formatClock(new Date());
    const requestCount = runTelemetry.requestCount + 1;
    setIsRunning(true);
    setError("");
    setResult(null);
    setRunTelemetry({
      elapsedMs: 0,
      finishedAtLabel: "",
      requestCount,
      startedAtLabel,
      startedAtMs,
      status: "running"
    });
    try {
      const response = await streamSummaryMeeting(
        {
          transcript,
          method,
          input_name: inputName.trim() || "frontend-input.md"
        },
        handleStreamEvent
      );
      setResult(response);
      setRunTelemetry({
        elapsedMs: performance.now() - startedAtMs,
        finishedAtLabel: formatClock(new Date()),
        requestCount,
        startedAtLabel,
        status: "success"
      });
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Summary request failed";
      setResult(null);
      setError(message);
      setRunTelemetry({
        elapsedMs: performance.now() - startedAtMs,
        finishedAtLabel: formatClock(new Date()),
        lastError: message,
        requestCount,
        startedAtLabel,
        status: "error"
      });
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark">09</div>
          <div>
            <p className="section-label">AIP491 research tool</p>
            <h1>Meeting Recap Studio</h1>
          </div>
        </div>
        <div className="header-status">
          <StatusPill isRunning={isRunning} error={error} result={result} />
          <div className="header-stat">
            <span>{transcriptStats.utteranceCount}</span>
            detected turns
          </div>
          <div className="header-stat">
            <span>{runTelemetry.requestCount}</span>
            browser runs
          </div>
        </div>
      </header>

      <section className="workspace">
        <form className="control-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <div>
              <p className="section-label">Run setup</p>
              <h2>Configure summary pass</h2>
            </div>
            <button className="run-button" type="submit" disabled={isRunning}>
              {isRunning ? "Running" : "Run"}
            </button>
          </div>

          <div className="config-grid">
            <label className="field">
              <span>Input name</span>
              <input value={inputName} onChange={(event) => setInputName(event.target.value)} />
            </label>
          </div>

          <fieldset className="method-picker">
            <legend>Summary method</legend>
            {METHOD_OPTIONS.map((option) => (
              <MethodChoice key={option.value} option={option} selected={method === option.value} onSelect={setMethod} />
            ))}
          </fieldset>

          <div className="local-model-card">
            <span>LOCAL</span>
            <strong>Local Ollama</strong>
            <small>Uses the backend local Ollama target on 127.0.0.1:11434.</small>
          </div>

          <label className="transcript-editor">
            <div className="editor-toolbar">
              <span>Transcript</span>
              <div className="editor-metrics">
                <strong>{transcriptStats.lineCount}</strong> lines
                <strong>{transcriptStats.wordCount}</strong> words
              </div>
            </div>
            <textarea spellCheck={false} value={transcript} onChange={(event) => setTranscript(event.target.value)} />
          </label>
        </form>

        <section className="report-panel" aria-live="polite">
          <div className="report-header">
            <div>
              <p className="section-label">Generated output</p>
              <h2>{result ? result.input_name : error ? "Run failed" : "Ready for analysis"}</h2>
            </div>
            <span className={`status ${error ? "error" : ""}`}>{getStatusText({ isRunning, error, result })}</span>
          </div>

          <MetricStrip stats={outputStats} transcriptStats={transcriptStats} />
          <RunDiagnostics telemetry={runTelemetry} result={result} isRunning={isRunning} error={error} />

          {error ? <ErrorPanel message={error} /> : result ? <ResultView result={result} selectedMethod={method} isRunning={isRunning} /> : isRunning ? <LoadingReport /> : <ResultView result={result} selectedMethod={method} isRunning={isRunning} />}
        </section>
      </section>
    </main>
  );

  function handleStreamEvent(streamEvent: SummaryStreamEvent) {
    if (streamEvent.event === "started") {
      setResult(streamEvent.data);
      return;
    }
    if (streamEvent.event === "method_completed") {
      setResult((current) => mergeMethodResult(current, streamEvent.data.method, streamEvent.data.result));
      return;
    }
    if (streamEvent.event === "completed") {
      setResult(streamEvent.data);
      return;
    }
    if (streamEvent.event === "error") {
      setError(streamEvent.data.detail || "Summary stream failed");
    }
  }
}

function MethodChoice({
  option,
  selected,
  onSelect
}: {
  option: (typeof METHOD_OPTIONS)[number];
  selected: boolean;
  onSelect: (method: SummaryMethod) => void;
}) {
  return (
    <label className={`method-choice ${selected ? "selected" : ""}`}>
      <input type="radio" name="method" value={option.value} checked={selected} onChange={() => onSelect(option.value)} />
      <span className="choice-kicker">{option.kicker}</span>
      <strong>{option.label}</strong>
      <small>{option.body}</small>
    </label>
  );
}

function StatusPill({ isRunning, error, result }: { isRunning: boolean; error: string; result: SummaryResponse | null }) {
  return <span className={`status ${error ? "error" : result ? "ready" : ""}`}>{getStatusText({ isRunning, error, result })}</span>;
}

function getStatusText({ isRunning, error, result }: { isRunning: boolean; error: string; result: SummaryResponse | null }) {
  if (isRunning) {
    return "Processing transcript";
  }
  if (error) {
    return "Needs attention";
  }
  if (result) {
    return result.model_targets[0]?.model || "Local Ollama";
  }
  return "Idle";
}

function MetricStrip({ stats, transcriptStats }: { stats: OutputStats; transcriptStats: TranscriptStats }) {
  return (
    <div className="metric-strip">
      <MetricCard label="Transcript turns" value={transcriptStats.utteranceCount} />
      <MetricCard label="Notes" value={stats.notes} />
      <MetricCard label="Tasks" value={stats.tasks} />
      <MetricCard label="Chapters" value={stats.chapters} />
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function RunDiagnostics({
  telemetry,
  result,
  isRunning,
  error
}: {
  telemetry: RunTelemetry;
  result: SummaryResponse | null;
  isRunning: boolean;
  error: string;
}) {
  const modelRuns = getModelRuns(result);
  const attempts = modelRuns.reduce((sum, run) => sum + (run.attempts || 0), 0);
  const failures = modelRuns.filter((run) => run.error).length;
  const totalModelSeconds = modelRuns.reduce((sum, run) => sum + (run.duration_seconds || 0), 0);
  const slowestRun = modelRuns.reduce<ModelRun | null>((slowest, run) => {
    if (!slowest || (run.duration_seconds || 0) > (slowest.duration_seconds || 0)) {
      return run;
    }
    return slowest;
  }, null);
  const target = getTargetSummary(result);
  const langfuse = getLangfuseSummary(result);

  return (
    <section className="diagnostics-panel">
      <div className="diagnostics-header">
        <div>
          <p className="section-label">Run diagnostics</p>
          <h3>{isRunning ? "Live request telemetry" : error ? "Last request failed" : result ? "Last request trace" : "No run yet"}</h3>
        </div>
        <span className={`diagnostic-state ${error ? "error" : result ? "ready" : isRunning ? "running" : ""}`}>{getTelemetryStatus(telemetry, isRunning, error)}</span>
      </div>

      <div className="diagnostic-grid">
        <DiagnosticMetric label="Wall time" value={formatDurationMs(telemetry.elapsedMs)} helper={telemetry.startedAtLabel ? `${telemetry.startedAtLabel}${telemetry.finishedAtLabel ? ` -> ${telemetry.finishedAtLabel}` : ""}` : "Waiting for first run"} />
        <DiagnosticMetric label="Browser request" value={telemetry.requestCount ? `#${telemetry.requestCount}` : "-"} helper="One POST /api/summarize per Run click" />
        <DiagnosticMetric label="Model requests" value={String(modelRuns.length)} helper="Backend model_runs captured from model stages" />
        <DiagnosticMetric label="Attempts" value={String(attempts)} helper="Includes retries when a stage fails" />
        <DiagnosticMetric label="Failures" value={String(failures)} helper={failures ? "Open the stage rows below" : "No model-stage errors recorded"} />
        <DiagnosticMetric label="Model time" value={formatSeconds(totalModelSeconds)} helper="Sum of backend stage durations" />
        <DiagnosticMetric label="Slowest task" value={slowestRun?.task || "-"} helper={slowestRun ? `${formatSeconds(slowestRun.duration_seconds || 0)} on ${slowestRun.target}` : "No completed model stage yet"} />
        <DiagnosticMetric label="Target" value={target.value} helper={target.helper} />
        <DiagnosticMetric label="Langfuse" value={langfuse.value} helper={langfuse.helper} />
      </div>

      {modelRuns.length ? (
        <div className="run-table">
          {modelRuns.map((run, index) => (
            <details className={`run-row ${run.error ? "has-error" : ""}`} key={`${run.task}-${index}`}>
              <summary>
                <span>{run.task}</span>
                <strong>{formatSeconds(run.duration_seconds || 0)}</strong>
                <em>{run.error ? "error" : "ok"}</em>
              </summary>
              <div className="run-row-meta">
                <span>{run.target || "unknown target"}</span>
                <span>{run.model || "model"}</span>
                <span>{run.attempts || 0} attempt(s)</span>
                {run.langfuse_observation_id ? <span>Langfuse {shortTraceId(run.langfuse_observation_id)}</span> : null}
              </div>
              {run.error ? <p className="run-error">{run.error}</p> : null}
              <details className="raw-preview">
                <summary>Raw preview</summary>
                <pre>{run.raw_preview || "No raw preview captured."}</pre>
              </details>
            </details>
          ))}
        </div>
      ) : (
        <p className="muted-text">{isRunning ? "Waiting for the server response. Stage-level details appear when the request finishes." : "Run a summary to see stage-level model calls, retries, durations, errors, and raw previews."}</p>
      )}
    </section>
  );
}

function DiagnosticMetric({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="diagnostic-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </div>
  );
}

function ResultView({
  result,
  selectedMethod,
  isRunning
}: {
  result: SummaryResponse | null;
  selectedMethod: SummaryMethod;
  isRunning: boolean;
}) {
  if (!result) {
    return (
      <div className="empty-state">
        <div className="empty-diagram">
          <span className="diagram-line" />
          <span className="diagram-node" />
          <span className="diagram-line short" />
        </div>
        <h3>No report generated yet</h3>
        <p>Paste a transcript, choose one or both methods, then run the summary pass. Output will render here from the live API response.</p>
      </div>
    );
  }

  return (
    <div className="result-grid">
      {result.results.highlights ? <HighlightsCard highlights={result.results.highlights} /> : null}
      {result.results.hierarchical ? <HierarchicalCard hierarchical={result.results.hierarchical} /> : null}
      {isRunning ? getPendingMethods(result, selectedMethod).map((methodName) => <PendingMethodCard methodName={methodName} key={methodName} />) : null}
    </div>
  );
}

function HighlightsCard({ highlights }: { highlights: HighlightsResult }) {
  return (
    <article className="method-card highlights-card">
      <MethodHeader kicker="DR1" title="Highlights Recap" meta={`${highlights.notes.length} notes / ${highlights.tasks.length} tasks`} />

      <div className="method-section">
        <h3>AI Notes</h3>
        <div className="summary-list">
          {highlights.notes.length ? highlights.notes.map((item, index) => <HighlightItemView item={item} key={`note-${index}`} kind="Note" />) : <EmptyText text="No notes generated." />}
        </div>
      </div>

      <div className="method-section">
        <h3>AI Tasks</h3>
        <div className="summary-list">
          {highlights.tasks.length ? highlights.tasks.map((item, index) => <HighlightItemView item={item} key={`task-${index}`} kind="Task" />) : <EmptyText text="No tasks generated." />}
        </div>
      </div>
    </article>
  );
}

function MethodHeader({ kicker, title, meta }: { kicker: string; title: string; meta: string }) {
  return (
    <div className="method-header">
      <span className="method-kicker">{kicker}</span>
      <div>
        <h2>{title}</h2>
        <p>{meta}</p>
      </div>
    </div>
  );
}

function HighlightItemView({ item, kind }: { item: HighlightItem; kind: "Note" | "Task" }) {
  return (
    <div className={`summary-item ${kind === "Task" ? "task-item" : ""}`}>
      <div className="summary-item-top">
        <span>{kind}</span>
        <small>U{item.source_utterance_id || "-"}</small>
      </div>
      <strong>{item.summary}</strong>
      {kind === "Task" ? (
        <dl className="task-meta">
          <div>
            <dt>Assignee</dt>
            <dd>{item.assignee || "-"}</dd>
          </div>
          <div>
            <dt>Due</dt>
            <dd>{item.due || "-"}</dd>
          </div>
        </dl>
      ) : null}
      <details>
        <summary>Source context</summary>
        <pre>{(item.context || []).map((line) => `U${line.id} ${line.speaker}: ${line.text}`).join("\n") || "No context"}</pre>
      </details>
    </div>
  );
}

function HierarchicalCard({ hierarchical }: { hierarchical: HierarchicalResult }) {
  return (
    <article className="method-card hierarchical-card">
      <MethodHeader kicker="DR2" title="Hierarchical Recap" meta={`${hierarchical.chapters.length} chapters`} />
      <div className="chapter-list">
        {hierarchical.chapters.length ? hierarchical.chapters.map((chapter) => <ChapterView chapter={chapter} key={chapter.chapter_number} />) : <EmptyText text="No chapters generated." />}
      </div>
    </article>
  );
}

function PendingMethodCard({ methodName }: { methodName: ConcreteSummaryMethod }) {
  const title = methodName === "highlights" ? "Highlights Recap" : "Hierarchical Recap";
  const kicker = methodName === "highlights" ? "DR1" : "DR2";
  return (
    <article className="method-card pending-method-card">
      <MethodHeader kicker={kicker} title={title} meta="Streaming from backend" />
      <LoadingReport />
    </article>
  );
}

function ChapterView({ chapter }: { chapter: Chapter }) {
  return (
    <section className="chapter">
      <div className="chapter-index">{String(chapter.chapter_number).padStart(2, "0")}</div>
      <div className="chapter-body">
        <div className="chapter-title-row">
          <h3>{chapter.title}</h3>
          <span>{chapter.timespan}</span>
        </div>
        <p>{chapter.summary}</p>
        <details open>
          <summary>{chapter.chunks.length} chunks / {chapter.utterance_ids.length} utterances</summary>
          {chapter.chunks.map((chunk) => (
            <ChunkView chunk={chunk} key={chunk.chunk_id} />
          ))}
        </details>
      </div>
    </section>
  );
}

function ChunkView({ chunk }: { chunk: Chunk }) {
  return (
    <div className="chunk">
      <div className="chunk-header">
        <strong>{chunk.chunk_id}</strong>
        <span>U{chunk.utterance_ids.join(", U")}</span>
      </div>
      <ul>
        {chunk.notes.map((note, index) => (
          <li key={`${chunk.chunk_id}-${index}`}>
            {note.summary} <span>{note.generated_by || ""}</span>
          </li>
        ))}
      </ul>
      <details>
        <summary>Raw transcript</summary>
        <pre>{chunk.utterances.map((item) => `U${item.id} ${item.speaker}: ${item.text}`).join("\n")}</pre>
      </details>
    </div>
  );
}

function LoadingReport() {
  return (
    <div className="loading-stack">
      <div className="skeleton wide" />
      <div className="skeleton-grid">
        <span />
        <span />
        <span />
      </div>
      <div className="skeleton tall" />
    </div>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="error-panel">
      <h3>Summary request failed</h3>
      <p>{message}</p>
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return <p className="muted-text">{text}</p>;
}

interface TranscriptStats {
  lineCount: number;
  wordCount: number;
  utteranceCount: number;
}

interface OutputStats {
  notes: number;
  tasks: number;
  chapters: number;
}

interface RunTelemetry {
  elapsedMs: number;
  finishedAtLabel: string;
  lastError?: string;
  requestCount: number;
  startedAtLabel: string;
  startedAtMs?: number;
  status: "idle" | "running" | "success" | "error";
}

function getTranscriptStats(text: string): TranscriptStats {
  const lines = text.split(/\n/).filter((line) => line.trim());
  const words = text.match(/[A-Za-zÀ-ỹ0-9_]+/g) || [];
  const utteranceCount = lines.filter((line) => /\(\d{1,2}:\d{2}(?::\d{2})?\s*-\s*\d{1,2}:\d{2}(?::\d{2})?\)\s*:/.test(line)).length;
  return {
    lineCount: lines.length,
    wordCount: words.length,
    utteranceCount
  };
}

function getOutputStats(result: SummaryResponse | null): OutputStats {
  if (!result) {
    return { notes: 0, tasks: 0, chapters: 0 };
  }
  return {
    notes: result.results.highlights?.notes.length || 0,
    tasks: result.results.highlights?.tasks.length || 0,
    chapters: result.results.hierarchical?.chapters.length || 0
  };
}

function getModelRuns(result: SummaryResponse | null): ModelRun[] {
  if (!result) {
    return [];
  }
  return [...(result.results.highlights?.model_runs || []), ...(result.results.hierarchical?.model_runs || [])];
}

function mergeMethodResult(
  current: SummaryResponse | null,
  methodName: ConcreteSummaryMethod,
  methodResult: HighlightsResult | HierarchicalResult
): SummaryResponse | null {
  if (!current) {
    return current;
  }
  return {
    ...current,
    results: {
      ...current.results,
      [methodName]: methodResult
    }
  };
}

function getPendingMethods(result: SummaryResponse, selectedMethod: SummaryMethod): ConcreteSummaryMethod[] {
  const expected: ConcreteSummaryMethod[] = selectedMethod === "both" ? ["highlights", "hierarchical"] : [selectedMethod];
  return expected.filter((methodName) => !result.results[methodName]);
}

function getTargetSummary(result: SummaryResponse | null): { value: string; helper: string } {
  if (!result || !result.model_targets.length) {
    return { value: "Local Ollama", helper: "http://127.0.0.1:11434" };
  }
  const target = result.model_targets[0];
  return { value: target.model || "Local Ollama", helper: target.base_url || "http://127.0.0.1:11434" };
}

function getLangfuseSummary(result: SummaryResponse | null): { value: string; helper: string } {
  if (!result) {
    return { value: "-", helper: "Waiting for first run" };
  }
  if (!result.langfuse_enabled) {
    return { value: "Disabled", helper: "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY" };
  }
  if (!result.langfuse_trace_id) {
    return { value: "Enabled", helper: "Trace id was not returned by the SDK" };
  }
  return { value: shortTraceId(result.langfuse_trace_id), helper: result.langfuse_trace_id };
}

function shortTraceId(value: string): string {
  if (!value) {
    return "-";
  }
  if (value.length <= 12) {
    return value;
  }
  return `${value.slice(0, 6)}...${value.slice(-6)}`;
}

function getTelemetryStatus(telemetry: RunTelemetry, isRunning: boolean, error: string): string {
  if (isRunning || telemetry.status === "running") {
    return "Running";
  }
  if (error || telemetry.status === "error") {
    return "Failed";
  }
  if (telemetry.status === "success") {
    return "Completed";
  }
  return "Idle";
}

function formatDurationMs(milliseconds: number): string {
  if (!milliseconds) {
    return "0.0s";
  }
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)}ms`;
  }
  return `${(milliseconds / 1000).toFixed(1)}s`;
}

function formatSeconds(seconds: number): string {
  if (!seconds) {
    return "0.0s";
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }
  return `${seconds.toFixed(2)}s`;
}

function formatClock(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
