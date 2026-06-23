/** Microphone capture and Gemini audio playback. */

export function bufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

export function base64ToBuffer(b64: string): ArrayBuffer {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export class AudioCapture {
  private _ctx: AudioContext | null = null;
  private _stream: MediaStream | null = null;
  private _worklet: AudioWorkletNode | null = null;
  private _source: MediaStreamAudioSourceNode | null = null;
  private _gain: GainNode | null = null;
  active = false;

  async start(onChunk: (buffer: ArrayBuffer) => void): Promise<void> {
    if (this.active) return;

    this._stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });

    this._ctx = new AudioContext();
    if (this._ctx.state === "suspended") await this._ctx.resume();

    await this._ctx.audioWorklet.addModule("/audio-processor.js");
    this._source = this._ctx.createMediaStreamSource(this._stream);
    this._worklet = new AudioWorkletNode(this._ctx, "pcm-audio-processor");
    this._gain = this._ctx.createGain();
    this._gain.gain.value = 0;

    this._worklet.port.onmessage = (ev: MessageEvent) => {
      if (ev.data?.type === "audio" && ev.data.buffer) {
        onChunk(ev.data.buffer as ArrayBuffer);
      }
    };

    this._source.connect(this._worklet);
    this._worklet.connect(this._gain);
    this._gain.connect(this._ctx.destination);
    this.active = true;
  }

  stop(): void {
    this.active = false;
    this._worklet?.disconnect();
    this._gain?.disconnect();
    this._source?.disconnect();
    this._stream?.getTracks().forEach((t) => t.stop());
    this._ctx?.close().catch(() => {});
    this._ctx = this._stream = this._worklet = this._source = this._gain = null;
  }
}

export class AudioPlayer {
  private _ctx: AudioContext | null = null;
  private _next = 0;
  private _sources = new Set<AudioBufferSourceNode>();
  private _muted = false;
  private readonly _rate = 24000;

  reset(): void {
    this.stop();
    this._muted = false;
  }

  /** Call on user gesture so playback is not blocked by autoplay policy. */
  prime(): void {
    const ctx = this._ctxReady();
    if (ctx?.state === "suspended") {
      void ctx.resume();
    }
  }

  mute(): void {
    this._muted = true;
    this.stop();
  }

  private _ctxReady(): AudioContext | null {
    if (this._muted) return null;
    if (!this._ctx) this._ctx = new AudioContext({ sampleRate: this._rate });
    if (this._ctx.state === "suspended") this._ctx.resume();
    return this._ctx;
  }

  play(buffer: ArrayBuffer): void {
    const ctx = this._ctxReady();
    if (!ctx) return;

    const int16 = new Int16Array(buffer);
    const f32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) f32[i] = int16[i] / 32768;

    const ab = ctx.createBuffer(1, f32.length, this._rate);
    ab.getChannelData(0).set(f32);
    const src = ctx.createBufferSource();
    src.buffer = ab;
    src.connect(ctx.destination);
    const t = Math.max(ctx.currentTime, this._next);
    src.start(t);
    this._next = t + ab.duration;
    this._sources.add(src);
    src.onended = () => this._sources.delete(src);
  }

  stop(): void {
    for (const src of this._sources) {
      try {
        src.stop();
      } catch {
        /* already stopped */
      }
    }
    this._sources.clear();
    this._next = 0;
    if (this._ctx) {
      this._ctx.close().catch(() => {});
      this._ctx = null;
    }
  }
}
