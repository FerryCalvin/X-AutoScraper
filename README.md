# Auto Scraper (Skripsi Project) 🎓

Web Application untuk melakukan scraping data Twitter/X secara otomatis, mendukung pencarian Parallel, Export CSV, dan Smart Mode (AI Expansion).

## ✨ Fitur Utama
*   **Web Interface**: Mudah digunakan tanpa coding.
*   **Parallel Scraping**: Menggunakan multiprocess untuk scraping ribuan tweet dalam hitungan detik.
*   **Smart Search 🧠**: Otomatis menemukan hashtag terkait untuk memperluas pencarian.
*   **Export CSV**: Siap untuk analisis data (SPSS/Python/Tableau).
*   **Rich Data**: Mengambil Likes, Retweets, Replies, Url, dan Timestamp.

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
