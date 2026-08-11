export type ProcessingState =
  | 'idle'
  | 'connecting'
  | 'recording'
  | 'paused'
  | 'finalizing'
  | 'degraded'
  | 'failed';

export interface AudioSessionStartPayload {
  sample_rate: number;
  channels: 1;
  settings: {
    echo_cancellation: boolean | null;
    noise_suppression: boolean | null;
    auto_gain_control: boolean | null;
  };
}

export interface AudioSessionSocketOptions {
  socketUrl: string;
  onEvent: (event: Record<string, unknown>) => void;
  onState: (state: ProcessingState) => void;
  onError: (error: Error) => void;
}

const MAX_PENDING_BYTES = 8 * 1024 * 1024;

export class AudioSessionSocket {
  private readonly options: AudioSessionSocketOptions;
  private socket: WebSocket | null = null;
  private pendingFrames: ArrayBuffer[] = [];
  private pendingBytes = 0;
  private ready = false;
  private finishing = false;
  private finishResolve: (() => void) | null = null;
  private finishReject: ((error: Error) => void) | null = null;

  constructor(options: AudioSessionSocketOptions) {
    this.options = options;
  }

  get bufferedAmount(): number {
    return (this.socket?.bufferedAmount ?? 0) + this.pendingBytes;
  }

  async open(start: AudioSessionStartPayload): Promise<void> {
    if (this.socket) throw new Error('Audio WebSocket is already active');
    const socket = new WebSocket(this.options.socketUrl);
    socket.binaryType = 'arraybuffer';
    this.socket = socket;

    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        reject(new Error('Timed out waiting for the ASR backend'));
      }, 15_000);

      socket.onopen = () => {
        socket.send(JSON.stringify({
          type: 'session_start',
          protocol_version: 1,
          ...start,
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
            const error = new Error(String(event.message ?? 'Audio pipeline failed'));
            this.options.onState('failed');
            this.options.onError(error);
          } else if (event.type === 'session_closed') {
            this.finishResolve?.();
            this.clearFinishHandlers();
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
        window.clearTimeout(timeout);
        if (this.finishing && this.finishReject) {
          this.finishReject(new Error('WebSocket closed before the session was finalized'));
          this.clearFinishHandlers();
        } else if (this.ready) {
          this.options.onState('failed');
          this.options.onError(new Error('The ASR backend connection closed unexpectedly'));
        }
      };
    });
  }

  send(frame: Float32Array): void {
    if (frame.length === 0) return;
    const payload = frame.slice().buffer as ArrayBuffer;
    if (this.ready && this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(payload);
      return;
    }
    if (this.pendingBytes + payload.byteLength > MAX_PENDING_BYTES) {
      const error = new Error('ASR backend is too slow; audio queue exceeded 8 MB');
      this.options.onState('failed');
      this.options.onError(error);
      throw error;
    }
    this.pendingFrames.push(payload);
    this.pendingBytes += payload.byteLength;
  }

  async finish(retain = true): Promise<void> {
    if (!this.ready || this.socket?.readyState !== WebSocket.OPEN) return;
    if (this.finishing) throw new Error('Audio session is already finalizing');
    this.finishing = true;
    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        this.clearFinishHandlers();
        reject(new Error('Timed out while finalizing the audio session'));
      }, 120_000);
      this.finishResolve = () => {
        window.clearTimeout(timeout);
        resolve();
      };
      this.finishReject = (error) => {
        window.clearTimeout(timeout);
        reject(error);
      };
      this.socket?.send(JSON.stringify({ type: 'session_end', retain }));
    });
  }

  close(): void {
    this.ready = false;
    this.finishing = false;
    this.pendingFrames = [];
    this.pendingBytes = 0;
    this.clearFinishHandlers();
    if (this.socket && this.socket.readyState < WebSocket.CLOSING) this.socket.close();
    this.socket = null;
  }

  private clearFinishHandlers(): void {
    this.finishResolve = null;
    this.finishReject = null;
  }
}
