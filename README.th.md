# Hermes Quota Panel — คู่มือสั้น

ตัวแสดงโควตา Codex / Claude บน Linux ใช้บัญชีที่ล็อกอินไว้ใน Hermes แล้ว

## ก่อนใช้งาน

ทดสอบบน **Ubuntu 24.04 + GNOME 46 + X11** เท่านั้น ยังไม่ยืนยันการจำตำแหน่งบน Wayland

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
