# Flight Price Tracker - ระบบติดตามราคาตั๋วเครื่องบิน

## สรุปภาพรวม

ระบบนี้ช่วยติดตามราคาตั๋วเครื่องบินจาก Google Flights **อัตโนมัติทุก 4 ชั่วโมง** แล้วแจ้งเตือนผ่าน LINE พร้อมบันทึกข้อมูลลง Google Sheets เพื่อวิเคราะห์แนวโน้มราคาและหาจังหวะซื้อตั๋วที่ดีที่สุด

## สถาปัตยกรรมระบบ (Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                System Cron (ทุก 4 ชม.)                    │
│                       │                                  │
│                       ▼                                  │
│   ┌──────────────────────────────────┐                   │
│   │  Flight Scraper (ตัวดึงข้อมูล)      │                   │
│   │  Python + Selenium + Chrome       │                   │
│   │  ดึงจาก Google Flights             │                   │
│   └──────────────┬───────────────────┘                   │
│                  │                                       │
│     ┌────────────┼────────────┬──────────────┐           │
│     ▼            ▼            ▼              ▼           │
│  ┌───────┐  ┌────────┐  ┌──────────┐  ┌──────────┐      │
│  │SQLite │  │  LINE  │  │ Google   │  │  CSV     │      │
│  │  DB   │  │  Flex  │  │ Sheets   │  │ Export   │      │
│  └───────┘  └────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────┘
```

## องค์ประกอบหลัก (Components)

### 1. Flight Scraper (`src/scraper.py`)
**ทำอะไร:** ดึงข้อมูลเที่ยวบินจาก Google Flights โดยใช้ Chrome headless

**ความสามารถ:**
- ค้นหาจากทุกสนามบิน (BKK สุวรรณภูมิ + DMK ดอนเมือง)
- ดึงราคาจากสายการบินโดยตรง + ตัวแทน 14 แห่ง (Agoda, Booking.com, Trip.com, Expedia ฯลฯ)
- ดึงข้อมูลสัมภาระ, เวลาเดินทาง, ประเภทเครื่องบิน
- ให้คะแนนเที่ยวบิน (Price Score + Time Score)
- Anti-detection เพื่อให้ Google แสดงข้อมูลครบ

**เครื่องมือ:** Python, Selenium, Chrome headless

### 2. ฐานข้อมูล (`src/database.py`)
**ทำอะไร:** เก็บข้อมูลราคาทั้งหมดในฐานข้อมูล SQLite

**เก็บอะไร:**
- ประวัติราคาทุกครั้งที่ดึง (เก็บ top 20 เที่ยวบินถูกสุดต่อเส้นทาง)
- สถิติ: ราคาต่ำสุดตลอดกาล, ราคาเฉลี่ย, แนวโน้มราคา
- ข้อมูลสัมภาระ, ตัวแทนจองที่ถูกที่สุด

**เครื่องมือ:** SQLite (ไม่ต้องติดตั้งอะไรเพิ่ม)

### 3. แจ้งเตือน LINE (`src/notifier.py`)
**ทำอะไร:** ส่งข้อความแจ้งเตือนราคาผ่าน LINE ทุก 4 ชม.

**แสดงอะไร:**
- ราคาถูกสุดจากทุกเส้นทาง/วัน
- ราคาจาก 3rd party ที่ถูกกว่า (เช่น Agoda ฿3,076 vs สายการบิน ฿3,370)
- เที่ยวบินไป-กลับรวมถูกสุด
- ข้อมูลสัมภาระ, เวลาเดินทาง
- **1 ข้อความต่อรอบ** (ประหยัดโควต้า LINE — ใช้ได้ 200 ข้อความ/เดือน)

**รูปแบบ:** LINE Flex Message (การ์ดสวยงาม ไม่ใช่ข้อความธรรมดา)

**เครื่องมือ:** LINE Messaging API (ฟรี 200 ข้อความ/เดือน)

### 4. Google Sheets Dashboard (`src/sheets_exporter.py`)
**ทำอะไร:** อัปเดต Google Sheets อัตโนมัติ เปิดดูได้จากมือถือ แชร์ให้เพื่อนได้

**5 แท็บ:**

| แท็บ | รายละเอียด |
|------|-----------|
| **Dashboard** | สรุปราคา, คำแนะนำ "ควรซื้อตอนนี้ไหม?", คะแนนเที่ยวบิน, ข้อมูลเครื่องบิน |
| **Overview** | ภาพรวมราคาถูกสุดต่อเส้นทาง |
| **All Flights** | ตารางเที่ยวบินทั้งหมด (เพิ่มข้อมูลทุกรอบ) |
| **Price History** | ประวัติราคาสำหรับทำกราฟแนวโน้ม |
| **Heatmap** | ตารางเปรียบเทียบราคาต่อวัน |

**เครื่องมือ:** Google Sheets API + gspread (ฟรี)

### 5. CSV Export (`src/exporter.py`)
**ทำอะไร:** บันทึกข้อมูลเป็นไฟล์ CSV สำรอง

### 6. ระบบให้คะแนน (Flight Scoring)
**ทำอะไร:** ให้คะแนนเที่ยวบินจาก 0-20 โดยรวม 2 ปัจจัย:

- **Price Score (0-10):** ยิ่งถูกยิ่งได้คะแนนสูง
- **Time Score (0-10):** 
  - ขาไป: ออกช่วงกลางวัน (10:00-14:00) ได้คะแนนสูง
  - ขากลับ: ถึง BKK ประมาณ 18:00 ได้คะแนนสูง

### 7. คำแนะนำซื้อตั๋ว (Buy Recommendation)
**ทำอะไร:** วิเคราะห์ว่าควรซื้อตั๋วตอนนี้หรือรอ

| สัญลักษณ์ | ความหมาย |
|-----------|---------|
| 🟢 BUY NOW | ราคาใกล้จุดต่ำสุด ควรซื้อเลย |
| 🟡 GOOD PRICE | ราคาดี ต่ำกว่าค่าเฉลี่ย |
| 🟡 WAIT | ราคายังลดอยู่ รอได้ |
| 🟠 RISKY | ราคาสูงกว่าค่าเฉลี่ย + กำลังขึ้น |
| 🔴 BUY NOW | เหลือไม่ถึง 2 สัปดาห์ ราคามักจะขึ้น |

---

## เทคโนโลยีที่ใช้ (Tech Stack)

| เทคโนโลยี | ใช้ทำอะไร | ค่าใช้จ่าย |
|-----------|---------|----------|
| Python 3.12 | ภาษาหลักของระบบ | ฟรี |
| Selenium + Chrome | ดึงข้อมูลจาก Google Flights | ฟรี |
| SQLite | ฐานข้อมูลเก็บประวัติราคา | ฟรี |
| LINE Messaging API | แจ้งเตือนราคาผ่าน LINE | ฟรี (200 ข้อความ/เดือน) |
| Google Sheets API | Dashboard ออนไลน์ | ฟรี |
| WSL2 (Ubuntu) | รันบน Windows | ฟรี |
| Cron | ตั้งเวลาทำงานอัตโนมัติ | ฟรี |

**ค่าใช้จ่ายทั้งหมด: ฿0 (ฟรีทั้งหมด)**

---

## วิธีแชร์ให้เพื่อนใช้กับทริปอื่น

### สิ่งที่ต้องเปลี่ยน:

**1. เปลี่ยนเส้นทางบิน** — แก้ไฟล์ `src/config.py`:
```python
SEARCH_ROUTES = [
    # เปลี่ยนเป็นเส้นทางที่ต้องการ เช่น กรุงเทพ-โตเกียว
    {"origin": "Bangkok", "destination": "Tokyo", "date": "2026-10-18", "label": "BKK-TYO-Oct18", "route_code": "BKK-TYO"},
    {"origin": "Tokyo", "destination": "Bangkok", "date": "2026-10-25", "label": "TYO-BKK-Oct25", "route_code": "TYO-BKK"},
]
```

**2. ตั้งค่า LINE Bot ใหม่** — ทำตามไกด์ `docs/LINE_SETUP.md`

**3. สร้าง Google Sheet ใหม่** — แชร์กับ service account email

**4. อัปเดต `.env`:**
```
LINE_CHANNEL_ACCESS_TOKEN=<token ใหม่>
LINE_USER_ID=<user id ใหม่>
GOOGLE_SHEET_ID=<sheet id ใหม่>
```

### สิ่งที่อาจต้องเพิ่ม:
- เพิ่มรหัสสนามบินใน `AIRPORT_SHORT` ถ้าบินเส้นทางใหม่
- เพิ่มสายการบินใน `AIRLINE_BAGGAGE` ถ้ามีสายการบินใหม่
- ปรับ Time Score ใน `_calc_time_score()` ถ้าต้องการเวลาที่ต่างออกไป

---

## โครงสร้างไฟล์

```
travelplan/
├── src/
│   ├── config.py           # ตั้งค่าเส้นทาง, สายการบิน, API keys
│   ├── scraper.py          # ดึงข้อมูลจาก Google Flights
│   ├── database.py         # จัดการฐานข้อมูล SQLite
│   ├── notifier.py         # ส่งแจ้งเตือน LINE
│   ├── sheets_exporter.py  # อัปเดต Google Sheets
│   ├── exporter.py         # Export เป็น CSV
│   └── main.py             # ตัวจัดการหลัก
├── data/                   # ฐานข้อมูล + CSV
├── logs/                   # บันทึกการทำงาน
├── docs/                   # เอกสาร
├── tests/                  # ชุดทดสอบ
├── requirements.txt        # Python packages
├── setup_cron.sh           # ตั้งเวลาอัตโนมัติ
└── .env                    # API keys (ไม่แชร์)
```

---

## วิธีติดตั้ง (สำหรับเพื่อนที่อยากใช้)

1. **ติดตั้ง WSL2 + Ubuntu** บน Windows
2. **ติดตั้ง Chrome:**
   ```bash
   wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
   sudo apt update && sudo apt install -y google-chrome-stable
   ```
3. **Clone โปรเจค + ติดตั้ง dependencies:**
   ```bash
   cd ~/travelplan
   pip3 install -r requirements.txt
   ```
4. **ตั้งค่า `.env`** ตามด้านบน
5. **ทดสอบ:**
   ```bash
   python3 src/main.py
   ```
6. **ตั้งเวลาอัตโนมัติ:**
   ```bash
   bash setup_cron.sh
   ```

---

## หมายเหตุ
- ระบบจะหยุดอัตโนมัติหลัง 1 เดือน (แก้ได้ที่ `SCRAPER_EXPIRY_DATE` ใน config)
- ต้องเปิดคอมพิวเตอร์ทิ้งไว้เพื่อให้ cron ทำงาน
- ข้อมูลทั้งหมดฟรี ไม่มีค่าใช้จ่าย
