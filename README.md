# Arknights IS Recorder

อัดวิดีโอ Arknights (PC) อัตโนมัติเมื่อกดปุ่ม **EXPLORE** ในโหมด Integrated Strategies — ได้ไฟล์ mp4 60fps พร้อมเสียงเกมและเสียงไมค์

## ต้องมี

- Windows + Arknights PC client
- Python 3.11+
- [ffmpeg](https://www.gyan.dev/ffmpeg/builds/) (full build ที่มี `ddagrab` และ `h264_nvenc`) อยู่ใน PATH
- การ์ดจอ NVIDIA (ใช้ NVENC เข้ารหัสวิดีโอ)

```bash
pip install -r requirements.txt
```

## วิธีใช้

```bash
python ark_is_recorder.py
```

1. กด Yes ที่ UAC — เกมรันแบบ admin โปรแกรมจึงต้องเป็น admin ด้วยถึงจะเห็นการคลิกในเกม
2. เข้าเกม กด **EXPLORE** → เริ่มอัด (หน้าต่าง console ขึ้น `● REC`)
3. กด **F10** → หยุดอัด แล้วรวมเสียงเข้าวิดีโอ
4. ไฟล์อยู่ใน `videos/`

ทดสอบตัวโปรแกรม: `python ark_is_recorder.py test`

## ปุ่มของแต่ละธีม

รูปใน `buttons/` คือคำว่า EXPLORE ของแต่ละธีม ใช้จับว่าคลิกโดนปุ่มไหม
ธีมใหม่: เปิดเกมเต็มจอ แคปด้วย Win+Shift+S **เฉพาะตัวหนังสือ EXPLORE** (ไม่เอาพื้นหลัง เพราะมันขยับ) แล้วเซฟเป็น .png ลงโฟลเดอร์นี้

## ค่าที่ปรับได้ (ต้นไฟล์ `ark_is_recorder.py`)

| ค่า | ใช้ทำอะไร |
|---|---|
| `THRESHOLD` | ความเหมือนขั้นต่ำของปุ่ม (ลดถ้ากดแล้วไม่อัด, เพิ่มถ้าปุ่มอื่นทำให้อัด) |
| `MARGIN` | ระยะ (px) รอบตัวหนังสือที่ยังนับว่าคลิกโดนปุ่ม |
| `MIC_GAIN` | ความดังเสียงไมค์ (0 = ไม่อัดไมค์) |
| `FPS` | เฟรมเรตของวิดีโอ |

## หมายเหตุ

- ทดสอบบนโน้ตบุ๊ก hybrid GPU (จอต่อกับ AMD iGPU, เข้ารหัสด้วย RTX 3050) — ffmpeg ถูกบังคับให้จับภาพผ่าน iGPU ด้วย `SHIM_MCCOMPAT`
- เกมต้องอยู่บนจอหลัก
- อัดทุกเสียงที่ออกลำโพง/หูฟังหลัก (รวมเสียง Discord) + ไมค์หลักของ Windows
