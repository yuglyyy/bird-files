import wave, struct, os, time
from datetime import datetime

OUT_DIR = os.environ.get("MOCK_OUT_DIR", "/opt/bird-files/record/data_temp/Audios")
DURATION_S = int(os.environ.get("MOCK_DURATION", "10"))
RATE = 44100
CHANNELS = 2
SAMPLE_WIDTH = 2  # S16_LE

os.makedirs(OUT_DIR, exist_ok=True)

def write_silence_wav(path, seconds):
    frames = RATE * seconds
    with wave.open(path, "w") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(RATE)
        zero = struct.pack("<h", 0) * CHANNELS
        chunk = 2048
        while frames > 0:
            n = min(chunk, frames)
            wf.writeframesraw(zero * n)
            frames -= n

if __name__ == "__main__":
    print(f"[mock_record] generating WAVs in {OUT_DIR} every {DURATION_S}s")
    while True:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out = os.path.join(OUT_DIR, f"{ts}.wav")
        write_silence_wav(out, DURATION_S)
        print(f"[mock_record] wrote {out}")
        time.sleep(60)
