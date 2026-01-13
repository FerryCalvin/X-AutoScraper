# Twitter/X Scraper - Node.js

Scraper Twitter menggunakan **rettiwt-api** untuk analisis sentimen.

## ⚠️ Penting

**Twitter telah memblokir semua akses guest/anonymous sejak Januari 2024.**  
Scraper ini memerlukan akun Twitter untuk berfungsi.

> 💡 **Tip**: Buat akun Twitter baru khusus untuk scraping, jangan gunakan akun utama!

## 🚀 Quick Start

### 1. Install

```bash
cd nodejs-scraper
npm install
```

### 2. Setup API Key (Pertama Kali)

```bash
node scraper.js --setup
```

Ikuti instruksi untuk mendapatkan cookies dari browser:
1. Login ke Twitter/X di browser
2. Buka Developer Tools (F12)
3. Tab Application → Cookies → twitter.com
4. Copy nilai `auth_token` dan `ct0`

### 3. Scrape!

```bash
# Scrape 100 tweets
node scraper.js -k "jokowi" -c 100

# Scrape 500 tweets dengan CSV output
node scraper.js -k "pilpres 2024" -c 500 --csv hasil.csv

# Scrape 1000 tweets
node scraper.js -k "indonesia" -c 1000
```

## 📋 CLI Options

| Option | Description |
|--------|-------------|
| `-k, --keyword` | Keyword pencarian (wajib) |
| `-c, --count` | Jumlah tweets (default: 100) |
| `-o, --output` | Nama file JSON output |
| `--csv` | Export ke CSV juga |
| `--setup` | Setup API key |

## 📁 Output

### JSON Format
```json
{
  "id": "1234567890",
  "text": "Tweet content...",
  "created_at": "2024-01-13T12:00:00",
  "like_count": 50,
  "retweet_count": 10,
  "user": {
    "username": "user123",
    "display_name": "User Name"
  }
}
```

## ⚠️ Troubleshooting

### "API key not found"
Jalankan `node scraper.js --setup` untuk setup API key.

### "401 Unauthorized"  
API key expired. Jalankan `--setup` ulang.

### Rate Limited
Tunggu 15 menit lalu coba lagi.

---
Built by **Friday** 🤖
