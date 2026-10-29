# Arknights IS Recorder

[English](#english) · [ภาษาไทย](#ภาษาไทย)

## English

Automatically records Arknights (PC) when you click **EXPLORE** in Integrated Strategies — a 60 fps mp4 with game audio and your microphone.

### Requirements

- Windows + the Arknights PC client
- Python 3.11+
- [ffmpeg](https://www.gyan.dev/ffmpeg/builds/) (a full build with `ddagrab` and `h264_nvenc`) on PATH
- An NVIDIA GPU (video is encoded with NVENC)

```bash
pip install -r requirements.txt
```

### Usage

```bash
python ark_is_recorder.py
```

1. Approve the UAC prompt — the game runs as admin, so the recorder must too in order to see clicks in the game
2. In the game, click **EXPLORE** → recording starts (the console shows `● REC`)
3. Press **F10** → recording stops and the audio is muxed in
4. Videos are saved in `videos/`

Self-test: `python ark_is_recorder.py test`

### Theme buttons

Each image in `buttons/` is one theme's EXPLORE text, used to tell whether a click landed on the button.
New theme: run the game fullscreen, capture **only the EXPLORE text** with Win+Shift+S (no background — it animates), and save it as a .png in that folder.

### Settings (top of `ark_is_recorder.py`)

| Setting | What it does |
|---|---|
| `THRESHOLD` | Minimum button similarity (lower it if EXPLORE doesn't start recording, raise it if other buttons do) |
| `MARGIN` | Distance (px) around the text that still counts as clicking the button |
| `MIC_GAIN` | Microphone volume (0 = don't record the mic) |
| `FPS` | Video frame rate |

### Notes

- Tested on a hybrid-GPU laptop (screen on an AMD iGPU, encoding on an RTX 3050); ffmpeg is forced onto the iGPU for capture with `SHIM_MCCOMPAT`
- The game must be on the primary monitor
- Records everything played through the default speakers/headset (Discord included) plus the default Windows microphone

## ภาษาไทย

อัดวิดีโอ Arknights (PC) อัตโนมัติเมื่อกดปุ่ม **EXPLORE** ในโหมด Integrated Strategies — ได้ไฟล์ mp4 60fps พร้อมเสียงเกมและเสียงไมค์

### ต้องมี

- Windows + Arknights PC client
- Python 3.11+
- [ffmpeg](https://www.gyan.dev/ffmpeg/builds/) (full build ที่มี `ddagrab` และ `h264_nvenc`) อยู่ใน PATH
- การ์ดจอ NVIDIA (ใช้ NVENC เข้ารหัสวิดีโอ)

```bash
pip install -r requirements.txt
```

### วิธีใช้

```bash
python ark_is_recorder.py
```

1. กด Yes ที่ UAC — เกมรันแบบ admin โปรแกรมจึงต้องเป็น admin ด้วยถึงจะเห็นการคลิกในเกม
2. เข้าเกม กด **EXPLORE** → เริ่มอัด (หน้าต่าง console ขึ้น `● REC`)
3. กด **F10** → หยุดอัด แล้วรวมเสียงเข้าวิดีโอ
4. ไฟล์อยู่ใน `videos/`

ทดสอบตัวโปรแกรม: `python ark_is_recorder.py test`

### ปุ่มของแต่ละธีม

รูปใน `buttons/` คือคำว่า EXPLORE ของแต่ละธีม ใช้จับว่าคลิกโดนปุ่มไหม
ธีมใหม่: เปิดเกมเต็มจอ แคปด้วย Win+Shift+S **เฉพาะตัวหนังสือ EXPLORE** (ไม่เอาพื้นหลัง เพราะมันขยับ) แล้วเซฟเป็น .png ลงโฟลเดอร์นี้

### ค่าที่ปรับได้ (ต้นไฟล์ `ark_is_recorder.py`)

| ค่า | ใช้ทำอะไร |
|---|---|
| `THRESHOLD` | ความเหมือนขั้นต่ำของปุ่ม (ลดถ้ากดแล้วไม่อัด, เพิ่มถ้าปุ่มอื่นทำให้อัด) |
| `MARGIN` | ระยะ (px) รอบตัวหนังสือที่ยังนับว่าคลิกโดนปุ่ม |
| `MIC_GAIN` | ความดังเสียงไมค์ (0 = ไม่อัดไมค์) |
| `FPS` | เฟรมเรตของวิดีโอ |

### หมายเหตุ

- ทดสอบบนโน้ตบุ๊ก hybrid GPU (จอต่อกับ AMD iGPU, เข้ารหัสด้วย RTX 3050) — ffmpeg ถูกบังคับให้จับภาพผ่าน iGPU ด้วย `SHIM_MCCOMPAT`
- เกมต้องอยู่บนจอหลัก
- อัดทุกเสียงที่ออกลำโพง/หูฟังหลัก (รวมเสียง Discord) + ไมค์หลักของ Windows
