/**
 * AudioWorklet — downsamples mic to 16 kHz PCM int16 chunks.
 */
class PCMAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._pos = 0;
    this._buf = [];
    this._CHUNK = 1600;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel?.length) return true;

    const step = sampleRate / 16000;
    let sumSq = 0;
    for (let i = 0; i < channel.length; i++) sumSq += channel[i] ** 2;
    const rms = Math.sqrt(sumSq / channel.length);

    while (this._pos < channel.length) {
      this._buf.push(channel[Math.floor(this._pos)]);
      this._pos += step;
    }
    this._pos -= channel.length;

    while (this._buf.length >= this._CHUNK) {
      const chunk = this._buf.splice(0, this._CHUNK);
      const int16 = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage({ type: "audio", buffer: int16.buffer, rms }, [int16.buffer]);
    }
    return true;
  }
}

registerProcessor("pcm-audio-processor", PCMAudioProcessor);
