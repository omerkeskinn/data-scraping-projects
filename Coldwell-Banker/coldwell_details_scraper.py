import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import chromedriver_autoinstaller

# Proje ana dizinine göre dinamik klasör yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_EXCEL_PATH = os.path.join(BASE_DIR, "data", "excel", "konut_ilan_linkleri.xlsx")
OUTPUT_EXCEL_PATH = os.path.join(BASE_DIR, "data", "excel", "ilan_detaylari.xlsx")

# ChromeDriver ve Selenium yapılandırması
chromedriver_autoinstaller.install()
chrome_options = Options()
chrome_options.page_load_strategy = 'normal'
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

try:
    # Input dosyasını kontrol et ve oku
    if not os.path.exists(INPUT_EXCEL_PATH):
        raise FileNotFoundError(f"Girdi dosyası bulunamadı: {INPUT_EXCEL_PATH}")

    df = pd.read_excel(INPUT_EXCEL_PATH)
    ilan_linkleri = df['Link'].tolist()
    ilan_detaylari = []

    # Her bir ilan linki için detayları çek
    for url in ilan_linkleri:
        try:
            driver.get(url)

            # Tablo verilerinin yüklendiğinden emin ol
            wait.until(EC.presence_of_element_located(
                (By.XPATH, '/html/body/section[2]/div/div/div[1]/div[3]/div[2]/div/div[1]/div/table')))

            ilan = {'Link': url}

            # İlan Detay Alanları
            try:
                ilan['Başlık'] = driver.find_element(By.XPATH, '/html/body/section[1]/div[1]/div/div[2]/div/div/h3').text
            except NoSuchElementException:
                ilan['Başlık'] = ''

            try:
                ilan['İlan No'] = driver.find_element(By.XPATH, '/html/body/section[1]/div[1]/div/div[1]/div/div/div/div/div').text
            except NoSuchElementException:
                ilan['İlan No'] = ''

            try:
                ilan['Konum'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Konum")]/td[2]').text
            except NoSuchElementException:
                ilan['Konum'] = ''

            try:
                ilan['Tapu Durumu'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Tapu Durumu")]/td[2]').text
            except NoSuchElementException:
                ilan['Tapu Durumu'] = ''

            try:
                ilan['Kategori'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Portföy Kategorisi")]/td[2]').text
            except NoSuchElementException:
                ilan['Kategori'] = ''

            try:
                ilan['Brüt Metrekare'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Metre Kare (Brüt)")]/td[2]').text
            except NoSuchElementException:
                ilan['Brüt Metrekare'] = ''

            try:
                ilan['Net Metrekare'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Metre Kare (Net)")]/td[2]').text
            except NoSuchElementException:
                ilan['Net Metrekare'] = ''

            try:
                ilan['Fiyat'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Fiyat")]/td[2]').text
            except NoSuchElementException:
                ilan['Fiyat'] = ''

            try:
                ilan['Oda Sayısı'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Oda Sayısı")]/td[2]').text
            except NoSuchElementException:
                ilan['Oda Sayısı'] = ''

            try:
                ilan['Bina Yaşı'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Bina Yaşı")]/td[2]').text
            except NoSuchElementException:
                ilan['Bina Yaşı'] = ''

            try:
                ilan['Toplam Kat Sayısı'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Kat Sayısı")]/td[2]').text
            except NoSuchElementException:
                ilan['Toplam Kat Sayısı'] = ''

            try:
                ilan['Bulunduğu Kat'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Bulunduğu Kat")]/td[2]').text
            except NoSuchElementException:
                ilan['Bulunduğu Kat'] = ''

            try:
                ilan['Kullanım Durumu'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Kullanım Durumu")]/td[2]').text
            except NoSuchElementException:
                ilan['Kullanım Durumu'] = ''

            try:
                ilan['Eşyalı'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Eşyalı")]/td[2]').text
            except NoSuchElementException:
                ilan['Eşyalı'] = ''

            try:
                ilan['Balkon'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Balkon")]/td[2]').text
            except NoSuchElementException:
                ilan['Balkon'] = ''

            try:
                ilan['Banyo Sayısı'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Banyo Sayısı")]/td[2]').text
            except NoSuchElementException:
                ilan['Banyo Sayısı'] = ''

            try:
                ilan['Isıtma'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Isıtma")]/td[2]').text
            except NoSuchElementException:
                ilan['Isıtma'] = ''

            try:
                ilan['Office ismi'] = driver.find_element(By.XPATH, '/html/body/section[1]/div[1]/div/div[2]/div/div/a').text
            except NoSuchElementException:
                ilan['Office ismi'] = ''

            try:
                ilan['Krediye Uygun'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Krediye Uygun")]/td[2]').text
            except NoSuchElementException:
                ilan['Krediye Uygun'] = ''

            try:
                ilan['GSM No'] = driver.find_element(By.XPATH, '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/ul[2]/li/a').text
            except NoSuchElementException:
                ilan['GSM No'] = ''

            try:
                ilan['İletişim Adı'] = driver.find_element(By.XPATH, '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[1]').text
            except NoSuchElementException:
                ilan['İletişim Adı'] = ''

            try:
                ilan['Mail'] = driver.find_element(By.XPATH, '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[3]').text
            except NoSuchElementException:
                ilan['Mail'] = ''

            # Görsel Linkleri
            for i in range(1, 6):
                try:
                    if i == 1:
                        xpath = '//*[@id="cb-item-gallery"]/div/div[4]/img'
                    else:
                        xpath = f'//*[@id="cb-item-gallery"]/ol/li[{i-1}]/img'
                    ilan[f'Resim {i} URL'] = driver.find_element(By.XPATH, xpath).get_attribute('src')
                except NoSuchElementException:
                    ilan[f'Resim {i} URL'] = ''

            try:
                ilan['Açıklama'] = driver.find_element(By.XPATH, '/html/body/section[2]/div/div/div[1]/div[2]/div[2]').text
            except NoSuchElementException:
                ilan['Açıklama'] = ''

            # Veri Temizleme ve Standartlaştırma
            try:
                dues_text = driver.find_element(By.XPATH, '//table//tr[contains(., "Aidat")]/td[2]').text
                ilan['Aidat'] = dues_text if 'TL' in dues_text or dues_text.isdigit() else {'Evet': 'Evet', 'Hayır': 'Hayır', 'Var': 'Evet', 'Yok': 'Hayır'}.get(dues_text, '')
            except NoSuchElementException:
                ilan['Aidat'] = ''

            try:
                deposit_text = driver.find_element(By.XPATH, '//table//tr[contains(., "Depozito")]/td[2]').text
                ilan['Depozito'] = {'Evet': 'Evet', 'Hayır': 'Hayır', 'Var': 'Evet', 'Yok': 'Hayır'}.get(deposit_text, deposit_text)
            except NoSuchElementException:
                ilan['Depozito'] = ''

            try:
                in_site_text = driver.find_element(By.XPATH, '//table//tr[contains(., "Site İçerisinde")]/td[2]').text
                ilan['Site içerisinde'] = {'Evet': 'Evet', 'Hayır': 'Hayır', 'Var': 'Evet', 'Yok': 'Hayır'}.get(in_site_text, '')
            except NoSuchElementException:
                ilan['Site içerisinde'] = ''

            try:
                ilan['Takasa Uygun'] = driver.find_element(By.XPATH, '//table//tr[contains(., "Takasa Uygun")]/td[2]').text
            except NoSuchElementException:
                ilan['Takasa Uygun'] = ''

            ilan_detaylari.append(ilan)

        except (TimeoutException, Exception) as e:
            print(f"URL işlenirken hata oluştu ({url}): {e}")
            continue

    # Verileri Excel'e kaydet
    df_detaylar = pd.DataFrame(ilan_detaylari)
    os.makedirs(os.path.dirname(OUTPUT_EXCEL_PATH), exist_ok=True)
    df_detaylar.to_excel(OUTPUT_EXCEL_PATH, index=False)
    print(f"İşlem tamamlandı. Toplam {len(ilan_detaylari)} ilan {OUTPUT_EXCEL_PATH} konumuna kaydedildi.")

finally:
    driver.quit()