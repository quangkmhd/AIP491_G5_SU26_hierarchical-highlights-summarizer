import {
  AudioSessionSocket,
  type ProcessingState,
} from './audioSessionSocket';

export type { ProcessingState } from './audioSessionSocket';

export interface MeetingAudioClientOptions {
  socketUrl: string;
  deviceId?: string;
  onEvent: (event: Record<string, unknown>) => void;
  onState: (state: ProcessingState) => void;
  onLevels: (levels: number[]) => void;
  onError: (error: Error) => void;
}

const QUIET_LEVELS = Array(8).fill(0.1) as number[];

const booleanSetting = (value: boolean | string | undefined): boolean | null => (
  typeof value === 'boolean' ? value : null
);

export class MeetingAudioClient {
  private readonly options: MeetingAudioClientOptions;
  private sessionSocket: AudioSessionSocket | null = null;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private worklet: AudioWorkletNode | null = null;
  private analyser: AnalyserNode | null = null;
  private sink: GainNode | null = null;
  private animationFrame: number | null = null;
  private ready = false;
  private paused = false;
  private stopping = false;

  constructor(options: MeetingAudioClientOptions) {
    this.options = options;
  }

  async start(): Promise<void> {
    if (this.sessionSocket || this.stream) {
      throw new Error('Audio session is already active');
    }
    this.options.onState('connecting');

    try {
      this.sessionSocket = new AudioSessionSocket({
        socketUrl: this.options.socketUrl,
        onEvent: this.options.onEvent,
        onState: (state) => {
          this.ready = state === 'recording' || state === 'degraded';
          this.options.onState(state);
        },
        onError: this.options.onError,
      });
      const audio: MediaTrackConstraints = {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        ...(this.options.deviceId
          ? { deviceId: { exact: this.options.deviceId } }
          : {}),
      };
      this.stream = await navigator.mediaDevices.getUserMedia({ audio });

      this.audioContext = new AudioContext();
      await this.audioContext.audioWorklet.addModule(
        new URL('./pcm-capture.worklet.ts', import.meta.url),
      );
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      this.source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 32;
      this.worklet = new AudioWorkletNode(this.audioContext, 'pcm-capture', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      this.sink = this.audioContext.createGain();
      this.sink.gain.value = 0;
      this.source.connect(this.analyser);
      this.source.connect(this.worklet);
      this.worklet.connect(this.sink).connect(this.audioContext.destination);
      this.worklet.port.onmessage = (message: MessageEvent<Float32Array | { type: string }>) => {
        if (message.data instanceof Float32Array) this.acceptFrame(message.data);
      };
      this.updateLevels();

      const track = this.stream.getAudioTracks()[0];
      if (!track) throw new Error('Microphone audio track is unavailable');
      const settings = track.getSettings();
      await this.sessionSocket.open({
        sample_rate: this.audioContext.sampleRate,
        channels: 1,
        settings: {
          echo_cancellation: booleanSetting(settings.echoCancellation),
          noise_suppression: booleanSetting(settings.noiseSuppression),
          auto_gain_control: booleanSetting(settings.autoGainControl),
        },
      });
      this.ready = true;
    } catch (cause) {
      const error = cause instanceof Error ? cause : new Error(String(cause));
      this.fail(error);
      throw error;
    }
  }

  pause(): void {
    if (!this.ready || this.stopping) return;
    this.paused = true;
    this.options.onLevels(QUIET_LEVELS);
    this.options.onState('paused');
  }

  resume(): void {
    if (!this.ready || this.stopping) return;
    this.paused = false;
    this.options.onState('recording');
  }

  async stop(retain = true): Promise<void> {
    if (this.stopping) return;
    this.stopping = true;
    this.paused = true;
    this.options.onLevels(QUIET_LEVELS);

    await this.flushWorklet();

    if (this.sessionSocket && this.ready) {
      this.options.onState('finalizing');
      try {
        await this.sessionSocket.finish(retain);
      } catch (cause) {
        const error = cause instanceof Error ? cause : new Error(String(cause));
        this.options.onError(error);
      }
    }

    await this.cleanup();
    this.options.onState('idle');
  }

  private acceptFrame(frame: Float32Array, allowStopping = false): void {
    if (((this.paused || this.stopping) && !allowStopping) || frame.length === 0) return;
    try {
      this.sessionSocket?.send(frame);
    } catch (cause) {
      this.fail(cause instanceof Error ? cause : new Error(String(cause)));
    }
  }

  private async flushWorklet(): Promise<void> {
    if (!this.worklet) return;
    await new Promise<void>((resolve) => {
      const timeout = window.setTimeout(resolve, 1_000);
      const listener = (message: MessageEvent<Float32Array | { type: string }>) => {
        if (message.data instanceof Float32Array) {
          this.acceptFrame(message.data, true);
        } else if (message.data.type === 'flushed') {
          window.clearTimeout(timeout);
          this.worklet?.port.removeEventListener('message', listener);
          resolve();
        }
      };
      this.worklet?.port.addEventListener('message', listener);
      this.worklet?.port.postMessage({ type: 'flush' });
    });
  }

  private updateLevels = (): void => {
    if (!this.analyser || !this.audioContext || this.audioContext.state === 'closed') return;
    if (!this.paused) {
      const bins = new Uint8Array(this.analyser.frequencyBinCount);
      this.analyser.getByteFrequencyData(bins);
      const step = Math.max(1, Math.floor(bins.length / 8));
      this.options.onLevels(Array.from({ length: 8 }, (_, index) => {
        const normalized = (bins[index * step] ?? 0) / 255;
        return Math.min(1, Math.max(0.1, normalized));
      }));
    }
    this.animationFrame = requestAnimationFrame(this.updateLevels);
  };

  private fail(error: Error): void {
    this.options.onState('failed');
    this.options.onError(error);
    void this.cleanup();
  }

  private async cleanup(): Promise<void> {
    this.ready = false;
    if (this.animationFrame !== null) cancelAnimationFrame(this.animationFrame);
    this.animationFrame = null;
    this.worklet?.disconnect();
    this.source?.disconnect();
    this.analyser?.disconnect();
    this.sink?.disconnect();
    this.worklet = null;
    this.source = null;
    this.analyser = null;
    this.sink = null;
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close();
    }
    this.audioContext = null;
    this.sessionSocket?.close();
    this.sessionSocket = null;
  }
}
