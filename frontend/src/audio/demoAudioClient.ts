import {
  AudioSessionSocket,
  type ProcessingState,
} from './audioSessionSocket';
import type { DemoTimelineItem, DemoTimelineManifest } from '../types';

const FRAME_SAMPLES = 1_600;
const BACKPRESSURE_SOFT_BYTES = 1024 * 1024;
const BACKPRESSURE_RESUME_BYTES = 256 * 1024;
const BACKPRESSURE_TIMEOUT_MS = 30_000;

export interface DemoProgress {
  recordingId: string | null;
  elapsedSamples: number;
  totalSamples: number;
}

export interface DemoTracePause {
  after_sample: number;
  started_epoch_ms: number;
  duration_ms: number;
}

export interface DemoTrace {
  completedRecordingIds: string[];
  maxConcurrentAudio: number;
  activeAudio: number;
  elapsedSamples: number;
  playbackStartedEpochMs: number | null;
  completedEpochMs: number | null;
  meetingCompleted: boolean;
  sessionClosed: boolean;
  pauses: DemoTracePause[];
  error: string | null;
}

declare global {
  interface Window {
    __vietAsrDemoTrace?: DemoTrace;
  }
}

export interface DemoAudioClientOptions {
  apiBaseUrl: string;
  socketUrl: string;
  onEvent: (event: Record<string, unknown>) => void;
  onState: (state: ProcessingState) => void;
  onProgress: (progress: DemoProgress) => void;
  onError: (error: Error) => void;
}

export class DemoAudioClient {
  private readonly options: DemoAudioClientOptions;
  private sessionSocket: AudioSessionSocket | null = null;
  private audioContext: AudioContext | null = null;
  private manifest: DemoTimelineManifest | null = null;
  private trace: DemoTrace | null = null;
  private elapsedSamples = 0;
  private currentRecordingId: string | null = null;
  private paused = false;
  private stopping = false;

  constructor(options: DemoAudioClientOptions) {
    this.options = options;
  }

  async start(): Promise<void> {
    if (this.sessionSocket || this.audioContext) {
      throw new Error('Demo audio session is already active');
    }
    this.options.onState('connecting');
    document.body.dataset.demoState = 'connecting';

    try {
      this.manifest = await this.fetchManifest();
      this.trace = {
        completedRecordingIds: [],
        maxConcurrentAudio: 0,
        activeAudio: 0,
        elapsedSamples: 0,
        playbackStartedEpochMs: null,
        completedEpochMs: null,
        meetingCompleted: false,
        sessionClosed: false,
        pauses: [],
        error: null,
      };
      window.__vietAsrDemoTrace = this.trace;

      this.audioContext = new AudioContext({ sampleRate: 16_000 });
      if (this.audioContext.state === 'suspended') await this.audioContext.resume();
      this.sessionSocket = new AudioSessionSocket({
        socketUrl: this.options.socketUrl,
        onEvent: (event) => this.handleServerEvent(event),
        onState: this.options.onState,
        onError: this.options.onError,
      });
      await this.sessionSocket.open({
        sample_rate: 16_000,
        channels: 1,
        settings: {
          echo_cancellation: null,
          noise_suppression: null,
          auto_gain_control: null,
        },
      });

      document.body.dataset.demoState = 'playing';
      this.options.onState('recording');
      for (const item of this.manifest.items) {
        if (this.stopping) return;
        await this.playItem(item);
        await this.emitSilence(item.gap_samples);
      }
      await this.emitSilence(this.manifest.padding_samples);
      this.trace.completedEpochMs = Date.now();

      document.body.dataset.demoState = 'finalizing';
      this.options.onState('finalizing');
      await this.sessionSocket.finish(true);
      if (!this.trace.meetingCompleted || !this.trace.sessionClosed) {
        throw new Error('Demo ended without meeting-completed and session_closed');
      }
      document.body.dataset.demoState = 'completed';
      this.options.onState('idle');
      await this.cleanup();
    } catch (cause) {
      const error = cause instanceof Error ? cause : new Error(String(cause));
      if (this.trace) this.trace.error = error.message;
      document.body.dataset.demoState = 'failed';
      this.options.onState('failed');
      this.options.onError(error);
      await this.cleanup();
      throw error;
    }
  }

  async pause(): Promise<void> {
    if (!this.audioContext || this.stopping || this.paused) return;
    this.paused = true;
    await this.audioContext.suspend();
    this.options.onState('paused');
  }

  async resume(): Promise<void> {
    if (!this.audioContext || this.stopping || !this.paused) return;
    this.paused = false;
    await this.audioContext.resume();
    this.options.onState('recording');
  }

  async stop(retain = true): Promise<void> {
    if (this.stopping) return;
    this.stopping = true;
    document.body.dataset.demoState = 'finalizing';
    this.options.onState('finalizing');
    try {
      await this.sessionSocket?.finish(retain);
    } finally {
      await this.cleanup();
      this.options.onState('idle');
    }
  }

  private async fetchManifest(): Promise<DemoTimelineManifest> {
    const response = await fetch(`${this.options.apiBaseUrl}/api/v1/demo/custom10h/manifest`);
    if (!response.ok) throw new Error(`Could not load demo manifest (${response.status})`);
    const manifest = await response.json() as DemoTimelineManifest;
    if (manifest.sample_rate !== 16_000 || !Array.isArray(manifest.items)) {
      throw new Error('Demo manifest must contain 16 kHz sequential audio');
    }
    return manifest;
  }

  private async playItem(item: DemoTimelineItem): Promise<void> {
    const context = this.requireAudioContext();
    this.reportProgress(item.recording_id);
    const response = await fetch(
      `${this.options.apiBaseUrl}/api/v1/demo/custom10h/audio/${encodeURIComponent(item.recording_id)}`,
    );
    if (!response.ok) throw new Error(`Could not load demo WAV ${item.recording_id}`);
    const decoded = await context.decodeAudioData(await response.arrayBuffer());
    if (decoded.numberOfChannels !== 1) {
      throw new Error(`Demo WAV ${item.recording_id} is not mono`);
    }
    if (decoded.sampleRate !== 16_000 || decoded.length !== item.sample_count) {
      throw new Error(`Demo WAV ${item.recording_id} does not match its manifest`);
    }

    const source = context.createBufferSource();
    source.buffer = decoded;
    source.connect(context.destination);
    const ended = new Promise<void>((resolve) => {
      source.onended = () => resolve();
    });
    if (!this.trace) throw new Error('Demo trace is unavailable');
    this.trace.activeAudio += 1;
    this.trace.maxConcurrentAudio = Math.max(
      this.trace.maxConcurrentAudio,
      this.trace.activeAudio,
    );
    if (this.trace.playbackStartedEpochMs === null) {
      this.trace.playbackStartedEpochMs = Date.now();
    }
    source.start();
    await this.emitFrames(decoded.getChannelData(0));
    await ended;
    source.disconnect();
    this.trace.activeAudio -= 1;
    this.trace.completedRecordingIds.push(item.recording_id);
  }

  private async emitFrames(samples: Float32Array): Promise<void> {
    const context = this.requireAudioContext();
    const startedAt = context.currentTime;
    for (let offset = 0; offset < samples.length; offset += FRAME_SAMPLES) {
      const targetTime = startedAt + offset / 16_000;
      await this.waitForAudioTime(targetTime);
      await this.waitForWritable();
      this.sessionSocket?.send(samples.subarray(offset, offset + FRAME_SAMPLES));
      this.elapsedSamples += Math.min(FRAME_SAMPLES, samples.length - offset);
      this.reportProgress(null);
    }
    await this.waitForAudioTime(startedAt + samples.length / 16_000);
  }

  private async emitSilence(sampleCount: number): Promise<void> {
    if (sampleCount <= 0) return;
    await this.emitFrames(new Float32Array(sampleCount));
  }

  private async waitForAudioTime(targetTime: number): Promise<void> {
    const context = this.requireAudioContext();
    while (context.currentTime < targetTime) {
      await new Promise((resolve) => window.setTimeout(resolve, 10));
    }
  }

  private async waitForWritable(): Promise<void> {
    if (!this.sessionSocket || this.sessionSocket.bufferedAmount <= BACKPRESSURE_SOFT_BYTES) {
      return;
    }
    const context = this.requireAudioContext();
    const startedEpochMs = Date.now();
    await context.suspend();
    while (this.sessionSocket.bufferedAmount > BACKPRESSURE_RESUME_BYTES) {
      if (Date.now() - startedEpochMs > BACKPRESSURE_TIMEOUT_MS) {
        throw new Error('ASR backend remained backpressured for 30 seconds');
      }
      await new Promise((resolve) => window.setTimeout(resolve, 25));
    }
    const durationMs = Date.now() - startedEpochMs;
    this.trace?.pauses.push({
      after_sample: this.elapsedSamples,
      started_epoch_ms: startedEpochMs,
      duration_ms: durationMs,
    });
    if (!this.paused) await context.resume();
  }

  private handleServerEvent(event: Record<string, unknown>): void {
    if (event.type === 'meeting-completed' && this.trace) this.trace.meetingCompleted = true;
    if (event.type === 'session_closed' && this.trace) this.trace.sessionClosed = true;
    this.options.onEvent(event);
  }

  private reportProgress(recordingId: string | null): void {
    if (!this.manifest) return;
    if (recordingId !== null) this.currentRecordingId = recordingId;
    if (this.trace) {
      this.trace.elapsedSamples = this.elapsedSamples;
    }
    this.options.onProgress({
      recordingId: this.currentRecordingId,
      elapsedSamples: this.elapsedSamples,
      totalSamples: this.manifest.duration_samples,
    });
  }

  private requireAudioContext(): AudioContext {
    if (!this.audioContext) throw new Error('Demo AudioContext is unavailable');
    return this.audioContext;
  }

  private async cleanup(): Promise<void> {
    this.sessionSocket?.close();
    this.sessionSocket = null;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close();
    }
    this.audioContext = null;
  }
}
