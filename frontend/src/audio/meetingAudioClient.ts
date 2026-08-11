export type ProcessingState =
  | 'idle'
  | 'connecting'
  | 'recording'
  | 'paused'
  | 'finalizing'
  | 'degraded'
  | 'failed';

export interface MeetingAudioClientOptions {
  socketUrl: string;
  deviceId?: string;
  onEvent: (event: Record<string, unknown>) => void;
  onState: (state: ProcessingState) => void;
  onLevels: (levels: number[]) => void;
  onError: (error: Error) => void;
}

const MAX_PENDING_BYTES = 8 * 1024 * 1024;
const QUIET_LEVELS = Array(8).fill(0.1) as number[];

export class MeetingAudioClient {
  private readonly options: MeetingAudioClientOptions;
  private socket: WebSocket | null = null;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private worklet: AudioWorkletNode | null = null;
  private analyser: AnalyserNode | null = null;
  private sink: GainNode | null = null;
  private animationFrame: number | null = null;
  private pendingFrames: ArrayBuffer[] = [];
  private pendingBytes = 0;
  private ready = false;
  private paused = false;
  private stopping = false;

  constructor(options: MeetingAudioClientOptions) {
    this.options = options;
  }

  async start(): Promise<void> {
    if (this.socket || this.stream) {
      throw new Error('Audio session is already active');
    }
    this.options.onState('connecting');

    try {
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

      await this.openSocket();
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

    if (this.socket?.readyState === WebSocket.OPEN && this.ready) {
      this.options.onState('finalizing');
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = window.setTimeout(
            () => reject(new Error('Timed out while finalizing the audio session')),
            120_000,
          );
          const finish = () => {
            window.clearTimeout(timeout);
            resolve();
          };
          const fail = () => {
            window.clearTimeout(timeout);
            reject(new Error('WebSocket closed before the session was finalized'));
          };
          this.socket?.addEventListener('message', (event) => {
            try {
              if (JSON.parse(String(event.data)).type === 'session_closed') finish();
            } catch {
              // The normal message handler reports malformed server messages.
            }
          }, { once: false });
          this.socket?.addEventListener('close', fail, { once: true });
          this.socket?.send(JSON.stringify({ type: 'session_end', retain }));
        });
      } catch (cause) {
        const error = cause instanceof Error ? cause : new Error(String(cause));
        this.options.onError(error);
      }
    }

    await this.cleanup();
    this.options.onState('idle');
  }

  private async openSocket(): Promise<void> {
    const track = this.stream?.getAudioTracks()[0];
    const context = this.audioContext;
    if (!track || !context) throw new Error('Microphone audio graph is unavailable');

    const settings = track.getSettings();
    const socket = new WebSocket(this.options.socketUrl);
    socket.binaryType = 'arraybuffer';
    this.socket = socket;

    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(
        () => reject(new Error('Timed out waiting for the ASR backend')),
        15_000,
      );
      socket.onopen = () => {
        socket.send(JSON.stringify({
          type: 'session_start',
          protocol_version: 1,
          sample_rate: context.sampleRate,
          channels: 1,
          settings: {
            echo_cancellation: settings.echoCancellation ?? null,
            noise_suppression: settings.noiseSuppression ?? null,
            auto_gain_control: settings.autoGainControl ?? null,
          },
        }));
      };
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(String(message.data)) as Record<string, unknown>;
          this.options.onEvent(event);
          if (event.type === 'session_ready') {
            window.clearTimeout(timeout);
            this.ready = true;
            for (const frame of this.pendingFrames) socket.send(frame);
            this.pendingFrames = [];
            this.pendingBytes = 0;
            this.options.onState('recording');
            resolve();
          } else if (event.type === 'processing_status' && event.degraded === true) {
            this.options.onState('degraded');
          } else if (event.type === 'pipeline_error') {
            this.options.onState('failed');
            this.options.onError(new Error(String(event.message ?? 'Audio pipeline failed')));
          }
        } catch (cause) {
          this.options.onError(new Error(`Invalid server message: ${String(cause)}`));
        }
      };
      socket.onerror = () => {
        window.clearTimeout(timeout);
        reject(new Error('Could not connect to the ASR backend'));
      };
      socket.onclose = () => {
        if (!this.stopping && this.ready) {
          this.fail(new Error('The ASR backend connection closed unexpectedly'));
        }
      };
    });
  }

  private acceptFrame(frame: Float32Array, allowStopping = false): void {
    if (((this.paused || this.stopping) && !allowStopping) || frame.length === 0) return;
    const payload = frame.slice().buffer as ArrayBuffer;
    if (this.ready && this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(payload);
      return;
    }
    if (this.pendingBytes + payload.byteLength > MAX_PENDING_BYTES) {
      this.fail(new Error('ASR backend is too slow; microphone queue exceeded 8 MB'));
      return;
    }
    this.pendingFrames.push(payload);
    this.pendingBytes += payload.byteLength;
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
    this.pendingFrames = [];
    this.pendingBytes = 0;
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
    if (this.socket && this.socket.readyState < WebSocket.CLOSING) this.socket.close();
    this.socket = null;
  }
}
