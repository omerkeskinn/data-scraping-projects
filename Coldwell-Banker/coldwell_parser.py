import os
from bs4 import BeautifulSoup
import pandas as pd

# Çalışma dizinine göre dinamik klasör yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FOLDER = os.path.join(BASE_DIR, "data", "html")
EXCEL_FOLDER = os.path.join(BASE_DIR, "data", "excel")
EXCEL_PATH = os.path.join(EXCEL_FOLDER, "listing_links.xlsx")

# İşlenecek HTML dosyalarının listesi
HTML_FILES = ["coldwell.html", "coldwell2.html", "coldwell3.html"]

# Tüm ilan linklerini saklamak için liste
all_links = []

# Her bir HTML dosyasını oku ve linkleri çek
for html_file in HTML_FILES:
    file_path = os.path.join(HTML_FOLDER, html_file)

    # Dosya var mı kontrol et
    if not os.path.exists(file_path):
        print(f"Uyarı: {file_path} dosyası bulunamadı, atlanıyor.")
        continue

    # HTML dosyasını oku
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

        # cb-list-item içindeki a etiketlerini bul
        list_items = soup.find_all("div", class_="cb-list-item")
        for item in list_items:
            link = item.find("a", href=True)
            if link and link["href"].startswith("https://www.cb.com.tr"):
                all_links.append(link["href"])

# Linkleri pandas DataFrame'ine dönüştür
df = pd.DataFrame(all_links, columns=["Listing Links"])

# Excel klasörü yoksa otomatik oluştur ve kaydet
os.makedirs(EXCEL_FOLDER, exist_ok=True)
df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")

print(f"İlan linkleri '{EXCEL_PATH}' dosyasına kaydedildi. Toplam {len(all_links)} link bulundu.")