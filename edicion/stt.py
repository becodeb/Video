import sys, json, wave, numpy as np, sherpa_onnx as so
M="models/sherpa-onnx-whisper-turbo/turbo-"
rec = so.OfflineRecognizer.from_whisper(encoder=M+"encoder.int8.onnx", decoder=M+"decoder.int8.onnx", tokens=M+"tokens.txt", language="es", task="transcribe", num_threads=4)
cfg = so.VadModelConfig(); cfg.silero_vad.model="models/silero_vad.onnx"; cfg.silero_vad.min_silence_duration=0.2; cfg.silero_vad.min_speech_duration=0.2; cfg.silero_vad.max_speech_duration=7; cfg.silero_vad.threshold=0.4; cfg.sample_rate=16000
for n in sys.argv[1:]:
    w=wave.open(f"aud/{n}.wav"); x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
    vad=so.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
    ws=512; out=[]
    def drain():
        while not vad.empty():
            s=vad.front; st=rec.create_stream(); st.accept_waveform(16000, np.array(s.samples)); rec.decode_stream(st)
            t0=s.start/16000; t1=t0+len(s.samples)/16000
            out.append({"start":round(t0,2),"end":round(t1,2),"text":st.result.text.strip()}); print(n,f"{t0:6.2f}-{t1:6.2f}",st.result.text.strip(),flush=True); vad.pop()
    for i in range(0,len(x),ws):
        vad.accept_waveform(x[i:i+ws]); drain()
    vad.flush(); drain()
    json.dump(out,open(f"aud/{n}.json","w"),ensure_ascii=False,indent=1)
