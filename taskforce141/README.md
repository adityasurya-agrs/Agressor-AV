
# TASK FORCE 141

DynamoDB Edition

## 1. Project Overview

TASK FORCE 141 adalah website simulasi cerita interaktif
bertema militer fiktif.

Fitur:
- Login dan registrasi pengguna.
- Penyimpanan akun menggunakan AWS DynamoDB.
- Lima pilihan role.
- Enam misi untuk setiap role.
- Dua belas keputusan per misi.
- Good ending dan bad ending.
- Sistem penguncian misi.
- Penyimpanan progres pengguna.
- Animasi radar dan background ringan.

## 2. Project Structure

task_force_141/
│
├── index.html
├── app.py
├── requirements.txt
└── README.md

## 3. AWS DynamoDB Setup

Buka AWS Console.

Masuk ke DynamoDB.

Pilih Create Table.

Gunakan konfigurasi:

Table name:
tf141_players

Partition key:
pk

Type:
String

Sort key:
sk

Type:
String

Table settings:
Customize settings

Capacity:
On-demand

## 4. IAM Role

EC2 harus memiliki IAM Role.

Berikan izin berikut pada tabel:

- dynamodb:GetItem
- dynamodb:PutItem
- dynamodb:UpdateItem

Contoh IAM Policy:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:ap-southeast-1:ACCOUNT_ID:table/tf141_players"
    }
  ]
}

Ganti ACCOUNT_ID dengan AWS Account ID milikmu.

Jangan memasukkan Access Key atau Secret Key
ke index.html maupun GitHub.

## 5. Install Dependencies

Masuk ke folder project:

cd task_force_141

Buat virtual environment:

python3 -m venv venv

Aktifkan:

source venv/bin/activate

Install:

pip install -r requirements.txt

## 6. Environment Variables

Contoh untuk pengujian HTTP lokal:

export AWS_REGION=ap-southeast-1

export DDB_TABLE=tf141_players

export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

export COOKIE_SECURE=false

Untuk website publik HTTPS, gunakan:

export COOKIE_SECURE=true

Gunakan secret key yang kuat dan tetap sama
setiap kali aplikasi dijalankan.

## 7. Test Backend

Jalankan:

python app.py

Backend berjalan pada:

http://127.0.0.1:5000

Tes:

http://127.0.0.1:5000/health

## 8. Production Server

Gunakan Gunicorn:

gunicorn --workers 2 --bind 127.0.0.1:5000 app:app

Jangan membuka port 5000 untuk publik.

## 9. Apache

Install:

sudo apt install apache2

Aktifkan modul:

sudo a2enmod proxy proxy_http headers

Buat file:

sudo nano /etc/apache2/sites-available/tf141.conf

Masukkan:

<VirtualHost *:80>
    ServerName domain-kamu.example

    ProxyPreserveHost On

    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/

    RequestHeader set X-Forwarded-Proto "https"
</VirtualHost>

Aktifkan:

sudo a2ensite tf141.conf

Periksa:

sudo apache2ctl configtest

Reload:

sudo systemctl reload apache2

Untuk penggunaan publik, aktifkan HTTPS
dan gunakan COOKIE_SECURE=true.

## 10. Testing

1. Buka website.
2. Buat akun.
3. Login.
4. Pilih role.
5. Mulai misi pertama.
6. Selesaikan 12 keputusan.
7. Periksa hasil ending.
8. Ulangi jika gagal.
9. Selesaikan misi untuk membuka misi selanjutnya.
10. Periksa progres di DynamoDB.

## 11. Database Structure

Contoh item:

pk:
USER#aditya

sk:
PROFILE

username:
aditya

password_hash:
HASHED_PASSWORD

role:
airborne

completed:
airborne#1
airborne#2

## 12. Security Notes

- Password disimpan sebagai hash.
- AWS SDK menggunakan IAM Role EC2.
- Jangan menyimpan AWS credentials di frontend.
- Gunakan HTTPS untuk website publik.
- Jangan upload secret key ke GitHub.
- Tambahkan CSRF protection dan rate limiting
  sebelum website digunakan secara publik.

Catatan:
Versi ini merupakan prototipe permainan.
Penilaian ending masih dilakukan di frontend,
sehingga belum cocok untuk progres kompetitif
yang harus tahan terhadap manipulasi pengguna.

S3 tidak digunakan.
Database menggunakan DynamoDB.
