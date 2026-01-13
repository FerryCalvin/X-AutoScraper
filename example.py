"""
Twitter Scraper - Contoh Penggunaan
Dibuat oleh Friday untuk teman-teman skripsi!

PENTING: Sebelum menggunakan scraper, pastikan sudah menambahkan akun Twitter!
Jalankan: python manage_accounts.py

Cara pakai scraper:
    python example.py --keyword "jokowi" --count 100
"""

import argparse
import asyncio
import sys
from scraper import TwitterScraper


def main():
    # Handle Windows event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="🐦 Twitter Scraper - Scrape tweets untuk analisis sentimen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PENTING: Sebelum menggunakan scraper, pastikan sudah menambahkan akun Twitter!
         Jalankan: python manage_accounts.py

Contoh penggunaan:
    python example.py --keyword "jokowi" --count 100
    python example.py --keyword "pilpres 2024" --count 500 --output hasil.json
    python example.py --keyword "indonesia" --count 1000 --csv hasil.csv
        """
    )
    
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        required=True,
        help="Keyword/topik yang ingin di-scrape"
    )
    
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=100,
        help="Jumlah tweet yang ingin diambil (default: 100)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file JSON (default: tweets_<keyword>.json)"
    )
    
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Export ke CSV juga (opsional)"
    )
    
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Sembunyikan progress bar"
    )
    
    args = parser.parse_args()
    
    # Create scraper
    print(f"\n🚀 Memulai scraping untuk keyword: '{args.keyword}'")
    print(f"   Target: {args.count} tweets\n")
    
    scraper = TwitterScraper()
    
    try:
        # Scrape tweets
        tweets = scraper.scrape(
            keyword=args.keyword,
            count=args.count,
            show_progress=not args.no_progress
        )
        
        if not tweets:
            print("\n❌ Tidak ada tweet yang ditemukan.")
            print("   Pastikan sudah menambahkan akun Twitter terlebih dahulu!")
            print("   Jalankan: python manage_accounts.py")
            return
        
        # Print summary
        scraper.print_summary(tweets)
        
        # Export JSON
        output_file = args.output or f"tweets_{args.keyword.replace(' ', '_')}.json"
        scraper.export_json(tweets, output_file)
        
        # Export CSV if requested
        if args.csv:
            scraper.export_csv(tweets, args.csv)
            
        print("\n✅ Selesai!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Dibatalkan oleh user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Tips: Pastikan sudah menambahkan akun Twitter!")
        print("   Jalankan: python manage_accounts.py")


if __name__ == "__main__":
    main()
