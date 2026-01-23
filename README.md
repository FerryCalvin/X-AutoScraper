# Auto Scraper (Skripsi Project) 🎓

Web Application untuk melakukan scraping data Twitter/X secara otomatis, mendukung pencarian Parallel, Export CSV, dan Smart Mode (AI Expansion).

## ✨ Fitur Utama
*   **Web Interface**: Mudah digunakan tanpa coding.
*   **Parallel Scraping**: Menggunakan multiprocess untuk scraping ribuan tweet dalam hitungan detik.
*   **Smart Search 🧠**: Otomatis menemukan hashtag terkait untuk memperluas pencarian.
*   **Batch Input & Queue 📝**: Masukkan banyak keyword sekaligus (comma separated), sistem akan menjalankannya satu per satu secara otomatis.
*   **Worker Settings 🛡️**: Pilihan mode aman (1 Worker) atau agresif (5 Workers).
*   **Auto Merge 📦**: Opsi untuk menggabungkan hasil batch menjadi satu file CSV.
*   **Rich Data**: Mengambil Likes, Retweets, Replies, Url, dan Timestamp.

## ⚠️ Risiko & Mitigasi (PENTING) 🚨
Aplikasi ini menggunakan teknik scraping yang powerful. Mohon perhatikan risiko berikut agar akun tetap aman:

| Pemicu Ban (Triggers) | Risiko | Mitigasi Aplikasi Ini |
| :--- | :--- | :--- |
| **Speeding** (Ngebut) | Akun dikunci sementara | Random Delay (1.5 - 4.0 detik) simulasi manusia. |
| **Pattern** (Pola Robot) | Terdeteksi Bot | Random Jitter (Waktu tidak pernah presisi). |
| **Concurrency** (Keroyokan) | **Shadowban / Suspend** | Gunakan **Safe Mode (1 Worker)** untuk akun utama. |
| **IP Reputation** | Blacklist IP | Gunakan Internet Rumah/HP. Hindari VPN Gratisan. |

**Rekomendasi Mode:**
*   **Demo Sidang / Akun Utama**: Gunakan **Safe Mode (1 Worker)**. Target < 500 tweet.
*   **Panen Data Besar**: Gunakan **Normal (3 Workers)** dengan Akun Cadangan.

## 🛠️ Cara Install (Untuk Pengguna Lain)

### 1. Clone Repository
```bash
git clone https://github.com/username/autoscraper.git
cd autoscraper
```

### 2. Install Dependencies
Pastikan sudah install Python 3.10+.
```bash
pip install -r requirements.txt
```

### 3. Setup Cookies (PENTING!) 🍪
Aplikasi ini membutuhkan login Twitter agar bisa mencari data tanpa batas.
1.  Buat file bernama `cookies_config.json` di dalam folder ini (sejajar dengan `.env`).
2.  Isi dengan format berikut (Ambil dari Browser > Inspect Element > Application > Cookies):

```json
{
    "auth_token": "paste_auth_token_disini",
    "ct0": "paste_ct0_disini"
}
```
*Note: File `cookies_config.json` ini RAHASIA dan tidak boleh di-upload ke GitHub.*

### 4. Jalankan Aplikasi
```bash
python app.py
```
Buka browser di `http://localhost:5000`

## ⚠️ Catatan Skripsi
Project ini menggunakan teknik Selenium Automation yang mensimulasikan browser manusia. Gunakan dengan bijak dan *delay* yang wajar untuk menghindari suspend akun.

## KILL SWITCH
taskkill /F /IM python.exe