/**
 * Microphone recorder that produces 16 kHz mono 16-bit WAV in the browser.
 * MediaRecorder gives WebM/Opus (Chrome) or MP4/AAC (Safari), which the Python side cannot decode
 * without ffmpeg; raw PCM written as WAV needs nothing. Stops by itself at Whisper's 30 s window.
 */
export const MAX_SECONDS = 30

export interface Recording {
  wav: Blob
  seconds: number
}

export class Recorder {
  private ctx: AudioContext | null = null
  private stream: MediaStream | null = null
  private node: ScriptProcessorNode | null = null
  private chunks: Float32Array[] = []
  private started = 0
  level = 0
  onLevel?: (level: number, seconds: number) => void
  onAutoStop?: () => void

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true },
    })
    this.ctx = new AudioContext()
    const src = this.ctx.createMediaStreamSource(this.stream)
    this.node = this.ctx.createScriptProcessor(4096, 1, 1)
    this.chunks = []
    this.started = performance.now()
    this.node.onaudioprocess = (e) => {
      const data = new Float32Array(e.inputBuffer.getChannelData(0))
      this.chunks.push(data)
      let sum = 0
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i]
      this.level = Math.min(1, Math.sqrt(sum / data.length) * 6)
      const seconds = (performance.now() - this.started) / 1000
      this.onLevel?.(this.level, seconds)
      if (seconds >= MAX_SECONDS) this.onAutoStop?.()
    }
    src.connect(this.node)
    this.node.connect(this.ctx.destination)
  }

  async stop(): Promise<Recording> {
    const rate = this.ctx?.sampleRate ?? 48000
    this.node?.disconnect()
    this.stream?.getTracks().forEach((t) => t.stop())
    await this.ctx?.close()
    this.ctx = null
    const total = this.chunks.reduce((n, c) => n + c.length, 0)
    const pcm = new Float32Array(total)
    let o = 0
    for (const c of this.chunks) {
      pcm.set(c, o)
      o += c.length
    }
    const mono16k = resample(pcm, rate, 16000)
    return { wav: toWav(mono16k, 16000), seconds: mono16k.length / 16000 }
  }

  cancel() {
    this.node?.disconnect()
    this.stream?.getTracks().forEach((t) => t.stop())
    void this.ctx?.close()
    this.ctx = null
    this.chunks = []
  }
}

/** Box-filtered decimation: average the input samples that fall into each output sample. */
function resample(input: Float32Array, from: number, to: number) {
  if (from === to) return input
  const ratio = from / to
  const out = new Float32Array(Math.floor(input.length / ratio))
  for (let i = 0; i < out.length; i++) {
    const a = Math.floor(i * ratio)
    const b = Math.min(input.length, Math.floor((i + 1) * ratio))
    let s = 0
    for (let j = a; j < b; j++) s += input[j]
    out[i] = s / Math.max(1, b - a)
  }
  return out
}

function toWav(samples: Float32Array, rate: number) {
  const buf = new ArrayBuffer(44 + samples.length * 2)
  const v = new DataView(buf)
  const str = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)))
  str(0, 'RIFF')
  v.setUint32(4, 36 + samples.length * 2, true)
  str(8, 'WAVE')
  str(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true)
  v.setUint16(22, 1, true)
  v.setUint32(24, rate, true)
  v.setUint32(28, rate * 2, true)
  v.setUint16(32, 2, true)
  v.setUint16(34, 16, true)
  str(36, 'data')
  v.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const x = Math.max(-1, Math.min(1, samples[i]))
    v.setInt16(44 + i * 2, x < 0 ? x * 0x8000 : x * 0x7fff, true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}
