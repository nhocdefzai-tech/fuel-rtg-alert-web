# Fuel RTG Alert Web

Du an web local de canh bao do dau RTG. Du an nay tach rieng voi shift report `E:\Learn\Python\AI\app.py`.

## Mo project

Mo VS Code bang file:

```text
E:\Learn\Python\fuel-rtg-alert-web\fuel-rtg-alert-web.code-workspace
```

Hoac chay:

```powershell
E:\Learn\Python\fuel-rtg-alert-web\OPEN_PROJECT.cmd
```

## Chay lan dau

Trong terminal VS Code, dam bao dang dung thu muc:

```powershell
PS E:\Learn\Python\fuel-rtg-alert-web>
```

Neu chua dung, chay:

```powershell
cd "E:\Learn\Python\fuel-rtg-alert-web"
```

Sau do chay:

```powershell
.\SETUP_ENV.cmd
.\RUN_WEB.cmd
```

Web se mo tai:

```text
http://127.0.0.1:8000
```

## Chay cho dien thoai/may tinh khac trong cung mang

Neu muon dien thoai hoac may tinh cong ty khac truy cap, chay:

```powershell
.\RUN_WEB_LAN.cmd
```

Terminal se hien URL dang:

```text
http://<IP_MAY_TINH>:8000
```

Vi du:

```text
http://192.168.1.25:8000
```

Mo URL do tren dien thoai hoac may tinh khac cung Wi-Fi/LAN.

Luu y:

- May chay app phai dang bat va khong tat terminal.
- Dien thoai/may khac phai cung mang noi bo.
- Neu khong truy cap duoc, Windows Firewall co the dang chan port `8000`; can Allow access cho Python/Flask khi Windows hoi.
- Khong nen mo app nay ra internet public vi hien chua co dang nhap.

## Cach su dung web

1. Upload `Fuel level .xlsx`.
2. Upload file TXT N4.
3. Bam `Them tau`.
4. Nhap ten tau, visit code neu co, ETB, ETD, priority.
5. Chon RTG 01-15 lien quan den tau.
6. Web tu dong luu sau moi lan nhap/sua.
7. Dashboard tu cap nhat canh bao thiet bi can do dau.
8. Bam `Download Excel` de tai `fuel_dashboard.xlsx`.

## Luu du lieu

Du lieu web duoc luu local tai:

```text
runtime\fuel_alert.db
runtime\uploads\
runtime\outputs\
```

Thu muc `runtime` bi `.gitignore`, khong dua len GitHub.

## Git va data that

Repo public chi nen commit code, README, tests va scripts.

Khong commit:

- `Fuel level .xlsx`
- `PHUONG - BAOVERVIEW.txt`
- file N4 that
- file Excel/TXT/CSV chua du lieu van hanh
- `runtime\fuel_alert.db`

`.gitignore` da chan cac file nay.

## Chay test

```powershell
.\RUN_TESTS.cmd
```

Hoac:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Lenh git local

Sau khi cai xong, project da co the khoi tao Git:

```powershell
git init
git add .
git commit -m "Initial fuel RTG alert web app"
```

De dua len GitHub public, tao repo rong tren GitHub roi chay:

```powershell
git remote add origin https://github.com/<your-user>/fuel-rtg-alert-web.git
git branch -M main
git push -u origin main
```
