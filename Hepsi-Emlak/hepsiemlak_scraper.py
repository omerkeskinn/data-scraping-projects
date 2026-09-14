import os
import time
import pandas as pd
import undetected_chromedriver as uc

# --- SABİT AYARLAR ---
EXCEL_FILE = "hepsi_emlak_URLS.xlsx"
BASE_URL = "https://www.hepsiemlak.com/harita/satilik/"
CHECK_INTERVAL = 1  # URL kontrol sıklığı (saniye)


def init_dataframe(file_path):
    """Excel dosyası varsa yükler, yoksa yeni bir DataFrame oluşturur."""
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return pd.DataFrame(columns=["İl", "İlçe", "URL"])


def parse_location_from_url(current_url):
    """URL yapısından İl ve İlçe bilgilerini ayrıştırır."""
    url_parts = current_url.split("/")
    
    if len(url_parts) > 4:
        location_raw = url_parts[-1].replace("-satilik", "").split("-")
        if len(location_raw) == 2:
            return location_raw[0], location_raw[1]
        elif len(location_raw) > 0:
            return location_raw[0], "Bilinmiyor"
            
    return "Bilinmiyor", "Bilinmiyor"


def main():
    df = init_dataframe(EXCEL_FILE)

    # Chrome sürücüsü konfigürasyonu
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")

    print("Tarayıcı başlatılıyor...")
    driver = uc.Chrome(options=options)

    try:
        driver.get(BASE_URL)
        last_url = driver.current_url

        print("\n[BİLGİ] Lütfen tarayıcı üzerinde il/ilçe seçip 'Ara' butonuna basın.")
        print("[BİLGİ] URL değişiklikleri otomatik takip ediliyor. Durdurmak için Ctrl+C yapabilirsiniz.\n")

        while True:
            current_url = driver.current_url
            
            if current_url != last_url:
                print(f"URL Değişikliği Algılandı: {current_url}")

                il, ilce = parse_location_from_url(current_url)

                # Yeni veriyi ekle ve kaydet
                new_row = pd.DataFrame({"İl": [il], "İlçe": [ilce], "URL": [current_url]})
                df = pd.concat([df, new_row], ignore_index=True)
                
                df.to_excel(EXCEL_FILE, index=False)
                print(f"-> Kaydedildi: İl={il} | İlçe={ilce}")

                last_url = current_url

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\nBir hata oluştu: {e}")
    finally:
        print("Tarayıcı kapatılıyor...")
        driver.quit()


if __name__ == "__main__":
    main()