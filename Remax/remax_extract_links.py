import os
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv

# .env dosyasını yükle (varsa)
load_dotenv()

# Çalışma dizinini dinamik olarak belirle (Kodun çalıştığı ana dizin)
BASE_DIR = Path(__file__).resolve().parent

# Klasör yollarını yapılandır (.env içerisinden de okunabilir)
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
HTML_DIR = DATA_DIR / "html"
OUTPUT_DIR = DATA_DIR / "output"

# Gerekli klasörler yoksa otomatik oluştur
HTML_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Kategorilere ait HTML ve çıktı Excel eşleştirmeleri
CATEGORIES = {
    "konut": {
        "html_file": "konut.html",
        "excel_file": "konut_ilan_linkleri.xlsx"
    },
    "arsa": {
        "html_file": "arsa.html",
        "excel_file": "arsa_ilan_linkleri.xlsx"
    },
    "ticari": {
        "html_file": "ticari.html",
        "excel_file": "ticari_ilan_linkleri.xlsx"
    }
}


def process_html_files():
    """HTML dosyalarını tarar, linkleri ayıklar ve Excel formatında kaydeder."""
    for category, info in CATEGORIES.items():
        html_path = HTML_DIR / info["html_file"]
        excel_path = OUTPUT_DIR / info["excel_file"]

        # HTML dosyasını oku
        try:
            with open(html_path, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file, "html.parser")
        except FileNotFoundError:
            print(f"[HATA] {html_path} dosyası bulunamadı! 'data/html/' klasörüne yerleştirdiğinizden emin olun.")
            continue
        except Exception as e:
            print(f"[HATA] {html_path} okunurken bir sorun oluştu: {e}")
            continue

        # İlan kartlarını bul (a.info)
        cards = soup.select("a.info")
        if not cards:
            print(f"[UYARI] {category} için ilan kartı (a.info) bulunamadı.")

        # Linkleri topla
        links = []
        for card in cards:
            href = card.get("href")
            if href:
                links.append({"ad_page_url": href})

        # Excel'e yaz
        if links:
            df = pd.DataFrame(links)
            df.to_excel(excel_path, index=False)
            print(f"[BAŞARILI] {category.capitalize()} için {len(links)} link {excel_path} dosyasına yazıldı.")
        else:
            print(f"[BİLGİ] {category.capitalize()} için dışa aktarılacak link bulunamadı.")

    print("\n[TAMAMLANDI] Bütün dosyalar işlendi!")


if __name__ == "__main__":
    process_html_files()