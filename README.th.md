# Hermes Quota Panel — คู่มือสั้น

ตัวแสดงโควตา Codex / Claude บน Linux ใช้บัญชีที่ล็อกอินไว้ใน Hermes แล้ว

## ก่อนใช้งาน

ทดสอบบน **Ubuntu 24.04 + GNOME 46 + X11** เท่านั้น ยังไม่ยืนยันการจำตำแหน่งบน Wayland ไม่มีการรองรับ Windows

## ติดตั้งแบบสะดวก — คำสั่งเดียว (แนะนำ)

โคลน repo (เป็น private ต้อง clone เอง ไม่มี curl-pipe-bash) แล้วรัน:

```sh
./setup.sh --dry-run    # ดูแผนก่อน ไม่เขียน/ติดตั้ง/เริ่มอะไรเลย
./setup.sh              # ตรวจ dependency GUI (ถามก่อน sudo apt-get ทุกครั้ง), หา Hermes,
                         # บันทึกค่า, ติดตั้ง+ตั้ง autostart ให้ผู้ใช้นี้, เริ่มสองตัวแสดงผลให้
```

- ถ้าขาด GUI package จะ **ถามยืนยันก่อนรัน sudo apt-get เสมอ**; ถ้ารันแบบไม่โต้ตอบ (non-interactive)
  หรือใส่ `--no-packages` จะไม่แตะ sudo เลย แค่พิมพ์คำสั่งให้ไปรันเอง
- ถ้าหา Hermes ไม่เจอหรือรุ่นไม่ตรง จะหยุดทันทีพร้อมคำอธิบาย ไม่ติดตั้ง/อัปเดต/ล็อกอิน Hermes ให้
  และไม่ขอรหัสผ่านใดๆ
- ถ้ามีตัวแสดงผลเดิมรันอยู่ หรือมี autostart รุ่นเก่า (`codex-quota.desktop`/`claude-quota.desktop`)
  จะ **ไม่เริ่มโปรแกรมใหม่และไม่เพิ่ม autostart ซ้ำ** แค่ติดตั้งไฟล์ไว้ แล้วแจ้งให้ย้ายเองด้วยมือ
- ส่วนเสริมคลิกตรง (GNOME 46) จะพยายามติดตั้งให้แบบ best-effort เท่านั้น อาจต้องออกแล้วเข้าระบบใหม่
  ก่อน Shell จะเจอ ไม่มีการันตีว่าใช้ได้ทันทีทุกเครื่อง

แฟล็กที่มี: `--dry-run`, `--no-packages`, `--no-start`, `--no-extension`

## ติดตั้งแบบแมนนวล (ควบคุมเองทีละขั้น)

```sh
sudo apt-get install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 librsvg2-common
python3 doctor.py
./launch.sh
./launch.sh --claude
```

## ติดตั้งแบบผู้ใช้ปัจจุบัน

```sh
python3 install.py --dry-run --autostart --extension
python3 install.py --autostart --extension
```

หลังออกแล้วเข้า Ubuntu ใหม่ จึงค่อยเปิดส่วนเสริม:

```sh
gnome-extensions enable quota-direct-click@hermes-quota-panel
```

- ปุ่ม Compact / Full สลับโหมดกะทัดรัด
- ลากหัวเพื่อย้าย ลากขอบเพื่อย่อ–ขยาย จำขนาดกับตำแหน่งร่วมกันทั้งสอง provider
- เลือกบัญชีเพื่อดูโควตา ไม่เปลี่ยนบัญชีที่บอตใช้งาน
- Refresh แค่ดึงข้อมูลใหม่ ส่วน Reset **ใช้เครดิตจริง** และต้องยืนยัน
- โควตา/ค่าตั้งส่วนตัวอยู่ใน `~/.local/state/hermes-quota-panel` ไม่อยู่ใน Git
- บัญชีและ token ไม่ได้มากับโปรแกรม ต้องใช้บัญชี Hermes ของคุณเอง

ถ้ามีตัวส่วนตัวรุ่นเก่ารันอยู่ ให้ปิด autostart และส่วนเสริมรุ่นเก่าด้วยตัวเองก่อนย้ายมาใช้รุ่นนี้ ตัวติดตั้งจะไม่ไปแก้ให้

ดูรายละเอียดการตั้ง path, เวลา, วิธีทดสอบ และข้อจำกัดใน README ภาษาอังกฤษ
