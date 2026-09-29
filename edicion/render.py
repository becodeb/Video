import sys, subprocess, os, time
from multiprocessing import Process
import edl
from lib import W, H, FPS

def work(k, a, b, out):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                          "-x264-params", "keyint=60:min-keyint=60:scenecut=0", out], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(a, b):
        im = edl.tl.frame(i / FPS)
        p.stdin.write(im.tobytes())
        if (i - a) % 300 == 0: print(f"[w{k}] {i-a}/{b-a} {time.time()-t0:.0f}s", flush=True)
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    nf = int(round(edl.TOTAL * FPS))
    a0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b0 = int(sys.argv[2]) if len(sys.argv) > 2 else nf
    nw = 4
    os.makedirs("parts", exist_ok=True)
    step = (b0 - a0 + nw - 1) // nw
    ps = []
    for k in range(nw):
        a, b = a0 + k * step, min(b0, a0 + (k + 1) * step)
        pr = Process(target=work, args=(k, a, b, f"parts/p{k}.mp4")); pr.start(); ps.append(pr)
    for pr in ps: pr.join()
    with open("parts/list.txt", "w") as f:
        for k in range(nw): f.write(f"file 'p{k}.mp4'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "parts/list.txt", "-c", "copy", "video_only.mp4"])
    print("done frames", a0, b0)
