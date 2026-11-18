# TASK FORCE 141

Game naratif berbasis web menggunakan Flask, AWS DynamoDB, dan HTML/CSS/JavaScript.

## Fitur

- Registrasi dan login; password disimpan sebagai hash.
- Session cookie HTTP-only, SameSite=Lax, Secure untuk HTTPS.
- Perlindungan CSRF pada endpoint yang mengubah data.
- Lima role: Infantry, Special Forces, Airborne, Air Force Pilot, dan Staff.
- Enam misi per role, masing-masing 12 tahap (360 tahap keseluruhan).
- Progres setiap role disimpan terpisah di DynamoDB.
- Misi berikutnya terbuka setelah misi sebelumnya berhasil.
- Pilihan pemain memengaruhi skor keputusan dan hasil misi.
- Flask/Gunicorn hanya listen di `127.0.0.1:5000`; Apache menjadi reverse proxy.

> Konflik dan cerita dalam game bersifat fiksi. Gameplay berfokus pada koordinasi, komunikasi, verifikasi informasi, keselamatan warga, dan pengambilan keputusan.

## Struktur repository

```text
TASK-FORCE-141/
├── frontend/
│   └── index.html
├── backend/
│   ├── app.py
│   └── requirements.txt
└── README.md
```

## 1. Persiapan AWS

Gunakan region `us-east-1`.

Buat DynamoDB table:
- Table name: `TF141`
- Partition key: `PK` (String)
- Sort key: `SK` (String)
- Capacity mode: On-demand

Pola item yang digunakan:
- `PK=USER#<username>`, `SK=PROFILE`
- `PK=USER#<username>`, `SK=ROLE#INFANTRY`
- `PK=USER#<username>`, `SK=ROLE#SPECIAL_FORCES`
- `PK=USER#<username>`, `SK=ROLE#AIRBORNE`
- `PK=USER#<username>`, `SK=ROLE#AIR_FORCE`
- `PK=USER#<username>`, `SK=ROLE#STAFF`

Pasang IAM Instance Profile pada EC2. Izin minimal untuk tabel `TF141`:
- `dynamodb:GetItem`
- `dynamodb:PutItem`
- `dynamodb:UpdateItem`

Arahkan Resource policy ke ARN tabel `TF141` di region `us-east-1`. Jangan menaruh AWS Access Key atau Secret Key di source code. Boto3 menggunakan kredensial sementara dari IAM Instance Profile.

## 2. Persiapan EC2

Contoh untuk Ubuntu Server 24.04 LTS:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install apache2 python3 python3-pip python3-venv git -y
sudo a2enmod proxy proxy_http headers
```

Security Group:
- SSH 22: My IP atau sumber EC2 Instance Connect yang sesuai.
- HTTP 80: `0.0.0.0/0`.
- HTTPS 443: `0.0.0.0/0`.
- Jangan membuka port 5000 ke internet.

## 3. Clone repository dari GitHub

Buat user service dan direktori aplikasi:

```bash
sudo adduser --system --group --home /home/tf141 --shell /usr/sbin/nologin tf141
sudo mkdir -p /opt/taskforce141
sudo chown tf141:tf141 /opt/taskforce141
```

Untuk repository public:

```bash
sudo -u tf141 git clone https://github.com/USERNAME/TASK-FORCE-141.git /opt/taskforce141
```

Ganti `USERNAME` dengan username GitHub milikmu. Untuk repository private, siapkan SSH Deploy Key di EC2 dan tambahkan public key pada repository GitHub. Jangan menaruh Personal Access Token di source code atau membagikannya.

Jika direktori atau user sudah ada dari percobaan sebelumnya, periksa kondisinya terlebih dahulu dan jangan membuat ulang secara membabi buta.

## 4. Buat virtual environment dan install dependencies

```bash
sudo -u tf141 python3 -m venv /opt/taskforce141/venv
sudo -u tf141 /opt/taskforce141/venv/bin/pip install --upgrade pip
sudo -u tf141 /opt/taskforce141/venv/bin/pip install -r /opt/taskforce141/backend/requirements.txt
```

## 5. Environment variables

Buat file konfigurasi di luar repository:

```bash
sudo nano /etc/taskforce141.env
```

Isi:

```env
FLASK_SECRET_KEY=GANTI_DENGAN_RANDOM_SECRET_YANG_PANJANG
AWS_DEFAULT_REGION=us-east-1
DDB_TABLE=TF141
COOKIE_SECURE=1
```

Buat secret key acak:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Salin hasilnya ke `FLASK_SECRET_KEY`. Jangan commit file `/etc/taskforce141.env` ke GitHub.

Atur izin:

```bash
sudo chown root:tf141 /etc/taskforce141.env
sudo chmod 640 /etc/taskforce141.env
```

`COOKIE_SECURE=1` digunakan setelah HTTPS aktif. Jika perlu menguji melalui HTTP sementara sebelum SSL dipasang, ubah sementara menjadi `COOKIE_SECURE=0`, restart service, lalu kembalikan ke `1` setelah HTTPS berfungsi.

## 6. Uji backend

```bash
sudo -u tf141 env FLASK_SECRET_KEY="temporary-local-test-key" AWS_DEFAULT_REGION="us-east-1" DDB_TABLE="TF141" COOKIE_SECURE=0 /opt/taskforce141/venv/bin/python /opt/taskforce141/backend/app.py
```

Dari terminal kedua:

```bash
curl http://127.0.0.1:5000/api/health
```

Hasil yang diharapkan:

```json
{"ok":true,"service":"TASK FORCE 141 API"}
```

Hentikan server pengujian dengan `Ctrl+C`. Jangan jalankan Flask development server sebagai layanan produksi. Pengujian ini tetap membutuhkan akses DynamoDB melalui IAM Instance Profile agar fitur akun dan progres berfungsi.

## 7. Buat systemd service

Buat:

```bash
sudo nano /etc/systemd/system/taskforce141.service
```

Isi:

```ini
[Unit]
Description=TASK FORCE 141 Flask Backend
After=network.target

[Service]
User=tf141
Group=www-data
WorkingDirectory=/opt/taskforce141/backend
EnvironmentFile=/etc/taskforce141.env
ExecStart=/opt/taskforce141/venv/bin/gunicorn --workers 1 --bind 127.0.0.1:5000 --timeout 30 app:app
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Aktifkan:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now taskforce141
sudo systemctl status taskforce141
```

Log:

```bash
sudo journalctl -u taskforce141 -n 50 --no-pager
```

## 8. Konfigurasi Apache

Frontend saja yang boleh menjadi DocumentRoot. Jangan jadikan folder repository sebagai DocumentRoot karena itu dapat mengekspos source code backend.

Buat virtual host:

```bash
sudo nano /etc/apache2/sites-available/taskforce141.conf
```

Ganti `DOMAIN_KAMU` dengan domain milikmu:

```apache
<VirtualHost *:80>
    ServerName DOMAIN_KAMU
    DocumentRoot /opt/taskforce141/frontend

    <Directory /opt/taskforce141/frontend>
        Options -Indexes
        AllowOverride None
        Require all granted
    </Directory>

    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:5000/api/
    ProxyPassReverse /api/ http://127.0.0.1:5000/api/

    ErrorLog ${APACHE_LOG_DIR}/tf141-error.log
    CustomLog ${APACHE_LOG_DIR}/tf141-access.log combined
</VirtualHost>
```

Aktifkan:

```bash
sudo a2ensite taskforce141.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Frontend dan API menggunakan origin yang sama. JavaScript memanggil endpoint relatif `/api/...`, jadi tidak memerlukan konfigurasi CORS.

## 9. DNS dan HTTPS

Arahkan DNS A record subdomain ke Public IPv4 EC2. Pastikan DNS sudah mengarah ke server dan HTTP dapat diakses sebelum meminta sertifikat.

```bash
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d DOMAIN_KAMU
sudo certbot renew --dry-run
```

Setelah HTTPS aktif, pastikan `COOKIE_SECURE=1` di `/etc/taskforce141.env`, lalu:

```bash
sudo systemctl restart taskforce141
```

## 10. Update dari GitHub

Setelah perubahan dikirim ke branch `main`:

```bash
sudo -u tf141 git -C /opt/taskforce141 pull origin main
sudo systemctl restart taskforce141
```

Jika hanya `frontend/index.html` yang berubah, Apache langsung menyajikan file terbaru tanpa restart Flask. Jika `requirements.txt` berubah:

```bash
sudo -u tf141 /opt/taskforce141/venv/bin/pip install -r /opt/taskforce141/backend/requirements.txt
sudo systemctl restart taskforce141
```

## Troubleshooting

```bash
sudo systemctl status apache2
sudo systemctl status taskforce141
sudo apache2ctl configtest
sudo journalctl -u taskforce141 -n 80 --no-pager
sudo tail -n 50 /var/log/apache2/tf141-error.log
curl http://127.0.0.1:5000/api/health
```

## Catatan keamanan dan batasan

- Aplikasi memerlukan DynamoDB dan IAM Instance Profile.
- `COOKIE_SECURE=1` memerlukan HTTPS agar browser mengirim session cookie.
- Gunakan HTTPS untuk penggunaan publik.
- Jangan membuka port 5000 ke internet.
- Jangan menyimpan password, secret key, AWS credentials, atau file `.env` di GitHub.
- Versi ini adalah fondasi awal; sebelum dipakai publik, tambahkan rate limiting, audit log, backup, dan pengujian keamanan.
- Progres misi tiap role disimpan pada item DynamoDB terpisah.
