"""Auto-record Arknights Integrated Strategies.

Click the IS EXPLORE button -> ffmpeg starts recording the game window. F10 stops.
Setup: crop each theme's EXPLORE text (+ emblem) with Win+Shift+S, save as .png in buttons/ next to this file.
       Crop tight: background art animates and gets covered by overlays, which kills the match.
Run:   python ark_is_recorder.py        (self-check: python ark_is_recorder.py test)
       It asks for admin (UAC): the game runs as admin, and Windows hides an admin window's clicks from others.
Needs: pip install opencv-python mss numpy PyAudioWPatch; ffmpeg on PATH; an NVIDIA GPU (h264_nvenc).
Output: 60 fps mp4 with system audio in videos/.
"""
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path

ctypes.windll.shcore.SetProcessDpiAwareness(2)  # mouse, mss and window rect all in physical pixels

import cv2, mss, numpy as np
import pyaudiowpatch as pyaudio

BUTTONS_DIR = Path(__file__).with_name("buttons")
THRESHOLD = 0.7  # lower if EXPLORE isn't detected, raise if other buttons trigger it
SCALES = (0.9, 0.95, 1.0, 1.05)  # covers the button's press animation and crops a few % off-size
MARGIN = 100  # px around the text crop that still counts as clicking EXPLORE (the button is bigger than its text)
OUT_DIR = Path(__file__).with_name("videos")
FPS = 60
MIC_GAIN = 1.0  # your voice (default Windows mic) mixed over game audio; raise if quiet, 0 = don't record the mic
VK_LBUTTON, VK_STOP = 0x01, 0x79  # left mouse, F10


def load_templates(paths):
    # imdecode instead of imread: imread breaks on Thai paths
    base = [cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_GRAYSCALE) for p in paths]
    return [cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) for t in base for s in SCALES]


def best_score(shot_gray, templates):
    """shot_gray is centred on the click; each template is searched only within MARGIN of the click."""
    cy, cx = shot_gray.shape[0] // 2, shot_gray.shape[1] // 2
    return max(cv2.minMaxLoc(cv2.matchTemplate(
        shot_gray[cy - h - MARGIN:cy + h + MARGIN, cx - w - MARGIN:cx + w + MARGIN], t, cv2.TM_CCOEFF_NORMED))[1]
        for t in templates for h, w in [t.shape])


def is_down(vk):
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def cursor_pos():
    p = wt.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def foreground_client_rect():
    u = ctypes.windll.user32
    hwnd = u.GetForegroundWindow()
    r, p = wt.RECT(), wt.POINT()
    u.GetClientRect(hwnd, ctypes.byref(r))
    u.ClientToScreen(hwnd, ctypes.byref(p))
    return p.x, p.y, r.right & ~1, r.bottom & ~1  # x264 needs even size


def record_audio(path):
    """Write system audio (+ mic) as raw float32 to `path` in a thread. Returns finish(), which stops it and
    returns (rate, channels); None when there's no speaker to listen to (the run is then recorded silent)."""
    pa = pyaudio.PyAudio()
    try:
        dev = pa.get_default_wasapi_loopback()
        rate, ch = int(dev["defaultSampleRate"]), dev["maxInputChannels"]
        speakers = pa.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultOutputDevice"]
        # float32 is WASAPI's shared-mode format. Playing silence keeps loopback delivering data while the game
        # is quiet; without it the audio would have gaps and drift out of sync.
        silence = pa.open(format=pyaudio.paFloat32, channels=ch, rate=rate, output=True, output_device_index=speakers,
                          stream_callback=lambda _in, n, _t, _s: (bytes(n * ch * 4), pyaudio.paContinue))
        loop = pa.open(format=pyaudio.paFloat32, channels=ch, rate=rate, input=True, input_device_index=dev["index"],
                       frames_per_buffer=1024)
    except (LookupError, OSError) as e:
        pa.terminate()
        print(f"! no system audio ({e}); recording video only")
        return None
    mic = open_mic(pa, rate) if MIC_GAIN else None
    stop = threading.Event()

    def run():
        # ponytail: assumes audio runs until F10; unplugging the headset mid-run ends it early and shifts it in add_audio
        try:
            with open(path, "wb") as f:
                while not stop.is_set():
                    data = loop.read(1024, exception_on_overflow=False)
                    if mic:  # same-size blocking reads keep the two streams in step; overflow drops absorb clock drift
                        data = mix_in_mic(data, mic.read(1024, exception_on_overflow=False), ch)
                    f.write(data)
        finally:
            for s in filter(None, (loop, mic, silence)):
                s.close()
            pa.terminate()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def finish():
        stop.set()
        thread.join()
        return rate, ch
    return finish


def open_mic(pa, rate):
    """Default Windows recording device, or None: a missing mic shouldn't cost the game audio."""
    try:
        dev = pa.get_device_info_by_index(pa.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultInputDevice"])
        if int(dev["defaultSampleRate"]) != rate:  # ponytail: no resampling; same-rate mics only
            print(f"! mic {dev['name']} runs at {int(dev['defaultSampleRate'])} Hz, not {rate}; recording without it")
            return None
        mic = pa.open(format=pyaudio.paFloat32, channels=dev["maxInputChannels"], rate=rate, input=True,
                      input_device_index=dev["index"], frames_per_buffer=1024)
    except (LookupError, OSError) as e:
        print(f"! no mic ({e}); recording game audio only")
        return None
    print(f"  mic: {dev['name']}")
    return mic


def mix_in_mic(game, voice, ch):
    """float32 bytes -> float32 bytes: mic downmixed to mono, added to every game channel, clipped."""
    g = np.frombuffer(game, np.float32).reshape(-1, ch)
    v = np.frombuffer(voice, np.float32).reshape(len(g), -1).mean(axis=1, keepdims=True)
    return np.clip(g + MIC_GAIN * v, -1, 1).astype(np.float32).tobytes()


def start_recording(x, y, w, h):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"IS_{datetime.now():%Y%m%d_%H%M%S}.mp4"
    # ddagrab (Desktop Duplication) holds 60 fps where gdigrab can't; NVENC keeps the CPU free for the game.
    # ponytail: assumes the game is on the primary monitor (output_idx=0) and an NVIDIA GPU for h264_nvenc.
    grab = f"ddagrab=output_idx=0:framerate={FPS}:offset_x={x}:offset_y={y}:video_size={w}x{h},hwdownload,format=bgra"
    # bgra goes straight to NVENC, which converts to yuv420p on the GPU: a CPU -pix_fmt conversion cost ~2.3 cores
    # (measured) and made the game stutter while recording; this way ffmpeg uses ~0.8 of a core.
    # Video only: with audio as a second live input, ffmpeg's scheduler stalled ddagrab waiting on the later-starting
    # audio (measured in-game: 30 frame-to-frame motion steps in 16 s vs 214 without). Audio is muxed in on stop.
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", grab, "-r", str(FPS),
           "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23",
           "-movflags", "+frag_keyframe+empty_moov", str(out)]  # fragmented mp4 stays playable if killed mid-run
    # On this hybrid laptop the screen hangs off the AMD iGPU; Desktop Duplication fails unless ffmpeg runs there.
    env = {**os.environ, "SHIM_MCCOMPAT": "0x800000000"}  # NVIDIA Optimus: run this process on the iGPU
    print(f"● REC  {out}  ({w}x{h} @ {FPS}fps)  — press F10 to stop")
    # Above normal: ffmpeg needs little CPU but must wake on time for every frame. At below-normal the game
    # starved it and recordings came out at ~13 effective fps (measured); at normal, the old CPU conversion lagged the game.
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, env=env, creationflags=subprocess.ABOVE_NORMAL_PRIORITY_CLASS)
    proc.finish_audio = record_audio(out.with_suffix(".audio.f32"))  # recorded alongside, muxed in on stop
    return proc


def stop_recording(proc):
    try:
        proc.stdin.write(b"q")  # 'q' lets ffmpeg finalize the file
        proc.stdin.close()
    except OSError:
        pass  # ffmpeg already exited
    fmt = proc.finish_audio() if proc.finish_audio else None  # stop audio at the same moment as the video
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("■ stopped")
    if fmt:
        add_audio(Path(proc.args[-1]), *fmt)


def add_audio(video, rate, ch):
    """Mux the separately recorded audio in. Audio starts before ddagrab is up, but both stop together, so the
    audio's extra length is exactly its early start: trim that off its front. Video is copied; audio encoded."""
    audio = video.with_suffix(".audio.f32")
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout
    try:
        lead = audio.stat().st_size / (4 * ch * rate) - float(probe)
    except (OSError, ValueError):
        print(f"! couldn't add audio; it's kept as {audio.name}")
        return
    fix = f"atrim=start={lead:.3f},asetpts=PTS-STARTPTS" if lead > 0 else f"adelay={-lead * 1000:.0f}:all=1"
    tmp = video.with_suffix(".synced.mp4")
    print(f"  adding audio (offset {lead * 1000:+.0f} ms)...")
    try:
        done = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
                               "-f", "f32le", "-ar", str(rate), "-ac", str(ch), "-i", str(audio),
                               "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", fix, "-c:a", "aac", "-b:a", "192k",
                               str(tmp)], creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)  # you may be playing on
    except KeyboardInterrupt:  # Ctrl+C mid-mux: drop the half-written copy, keep video + raw audio
        tmp.unlink(missing_ok=True)
        raise
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        print(f"! couldn't add audio; it's kept as {audio.name}")
        return
    try:
        tmp.replace(video)  # only swap once the muxed copy is complete; the original survives any failure
    except PermissionError:  # original open in a player or Explorer preview: keep both
        print(f"! {video.name} is open in another program; the version with audio is {tmp.name}")
    audio.unlink()


def relaunch_as_admin():
    # cmd /k keeps the elevated console open so its output (or an error) stays readable after exit
    script = Path(__file__).resolve()
    ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f'/k ""{sys.executable}" "{script}""', None, 1)


def main():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        relaunch_as_admin()
        sys.exit("Opened an admin window for the recorder (approve the UAC prompt).")
    paths = sorted(BUTTONS_DIR.glob("*.png"))
    if not paths:
        sys.exit(f"No .png in {BUTTONS_DIR}: crop each theme's EXPLORE button (Win+Shift+S) and save it there.")
    templates = load_templates(paths)
    th, tw = max(t.shape[0] for t in templates) + MARGIN, max(t.shape[1] for t in templates) + MARGIN
    print(f"Loaded {len(paths)} button(s). Waiting for IS EXPLORE click... (Ctrl+C to quit)")

    # Plain polling: no hook DLL or extra dependency, and it sees the game's clicks once we run as admin.
    proc = None
    was_click = was_stop = False
    with mss.MSS() as sct:
        try:
            while True:
                time.sleep(0.01)
                click, stop = is_down(VK_LBUTTON), is_down(VK_STOP)
                new_click, new_stop = click and not was_click, stop and not was_stop
                was_click, was_stop = click, stop
                recording = proc is not None and proc.poll() is None
                if proc is not None and not recording and not new_stop:
                    print(f"! ffmpeg stopped on its own (exit {proc.returncode}); keeping what was recorded")
                    stop_recording(proc)  # still stops the audio and muxes it in
                    proc = None
                if new_stop:
                    if recording:
                        stop_recording(proc)
                    proc = None
                elif new_click and not recording:
                    x, y = cursor_pos()
                    shot = np.array(sct.grab({"left": x - tw, "top": y - th, "width": 2 * tw, "height": 2 * th}))
                    score = best_score(cv2.cvtColor(shot, cv2.COLOR_BGRA2GRAY), templates)
                    if score >= THRESHOLD:
                        proc = start_recording(*foreground_client_rect())
                    elif score >= 0.6:  # ordinary UI text (terminal, Explorer) scores ~0.5
                        try:
                            cv2.imencode(".png", shot)[1].tofile(Path(__file__).with_name("near_miss.png"))
                        except OSError:
                            pass  # file open in a viewer; the debug image isn't worth crashing over
                        print(f"near miss: score {score:.2f} < THRESHOLD {THRESHOLD} (what it saw: near_miss.png)")
        except KeyboardInterrupt:
            pass
        finally:
            if proc is not None:  # Ctrl+C reaches ffmpeg too, so it may already be gone; the audio still needs muxing
                stop_recording(proc)


def selftest():
    rng = np.random.default_rng(0)
    templates = [rng.integers(0, 255, (40, 120), dtype=np.uint8), rng.integers(0, 255, (30, 90), dtype=np.uint8)]
    th, tw = 40 + MARGIN, 120 + MARGIN  # same shot size main() grabs; click is at the centre (th, tw)

    def scene_with(top, left):
        scene = rng.integers(0, 255, (2 * th, 2 * tw), dtype=np.uint8)
        scene[top:top + 30, left:left + 90] = templates[1]  # any theme's button counts
        return scene

    assert best_score(rng.integers(0, 255, (2 * th, 2 * tw), dtype=np.uint8), templates) < THRESHOLD  # no button
    assert best_score(scene_with(th - 15, tw - 45), templates) >= THRESHOLD  # click on the text
    assert best_score(scene_with(th + MARGIN // 2, tw - 45), templates) >= THRESHOLD  # click above, within MARGIN
    assert best_score(scene_with(th - 15, tw + MARGIN + 30), templates) < THRESHOLD  # text too far right of click
    darker = (scene_with(th - 15, tw - 45) * 0.7).astype(np.uint8)
    assert best_score(darker, templates) >= THRESHOLD  # darker "pressed" state still matches

    game = np.array([[0.5, -0.5], [0.9, 0.0]], np.float32)  # 2 frames, stereo
    voice = np.array([[0.2, 0.2], [0.4, 0.0]], np.float32)  # stereo mic -> mono 0.2, 0.2
    mixed = np.frombuffer(mix_in_mic(game.tobytes(), voice.tobytes(), 2), np.float32).reshape(-1, 2)
    assert np.allclose(mixed, [[0.5 + 0.2 * MIC_GAIN, -0.5 + 0.2 * MIC_GAIN],
                               [min(0.9 + 0.2 * MIC_GAIN, 1), 0.2 * MIC_GAIN]]), mixed  # clipped at 1

    import tempfile  # add_audio: 2 s video + 2.5 s raw audio (= audio started 0.5 s early) -> audio trimmed to 2 s
    with tempfile.TemporaryDirectory() as d:
        clip = Path(d) / "clip.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=2:r=60", "-c:v", "libx264",
                        str(clip)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=d=2.5:sample_rate=48000", "-ac", "2",
                        "-f", "f32le", str(clip.with_suffix(".audio.f32"))], check=True)
        add_audio(clip, 48000, 2)
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=duration", "-of", "csv=p=0",
                              str(clip)], capture_output=True, text=True).stdout.split()
        assert len(out) == 2 and abs(float(out[0]) - float(out[1])) < 0.05, out
        assert not clip.with_suffix(".audio.f32").exists()  # raw audio cleaned up once muxed
    print("selftest ok")


if __name__ == "__main__":
    selftest() if sys.argv[1:] == ["test"] else main()
