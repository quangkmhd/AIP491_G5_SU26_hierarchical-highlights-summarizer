declare class AudioWorkletProcessor {
  readonly port: MessagePort;
}

declare const registerProcessor: (
  name: string,
  processorCtor: typeof AudioWorkletProcessor,
) => void;

class PcmCaptureProcessor extends AudioWorkletProcessor {
  private readonly frame = new Float32Array(2048);
  private offset = 0;

  constructor() {
    super();
    this.port.onmessage = (event: MessageEvent<{ type?: string }>) => {
      if (event.data?.type !== 'flush') return;
      this.emitFrame();
      this.port.postMessage({ type: 'flushed' });
    };
  }

  process(inputs: Float32Array[][]): boolean {
    const input = inputs[0]?.[0];
    if (!input?.length) return true;

    let inputOffset = 0;
    while (inputOffset < input.length) {
      const count = Math.min(input.length - inputOffset, this.frame.length - this.offset);
      this.frame.set(input.subarray(inputOffset, inputOffset + count), this.offset);
      this.offset += count;
      inputOffset += count;
      if (this.offset === this.frame.length) this.emitFrame();
    }
    return true;
  }

  private emitFrame(): void {
    if (this.offset === 0) return;
    const output = this.frame.slice(0, this.offset);
    this.offset = 0;
    this.port.postMessage(output, [output.buffer]);
  }
}

registerProcessor('pcm-capture', PcmCaptureProcessor);

export {};
