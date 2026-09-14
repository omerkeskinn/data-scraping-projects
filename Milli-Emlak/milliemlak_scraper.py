import os
import re
import time
import pandas as pd
import chromedriver_autoinstaller
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- PROJE DİZİN YAPISI (Görünür Yerel Yollar Kaldırıldı) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HTML_DIR = os.path.join(DATA_DIR, "html")
EXCEL_DIR = os.path.join(DATA_DIR, "excel")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# Klasörleri otomatik oluştur
for folder in [HTML_DIR, EXCEL_DIR, LOGS_DIR]:
    os.makedirs(folder, exist_ok=True)

MERGED_EXCEL_PATH = os.path.join(EXCEL_DIR, "ilan_links_merged.xlsx")
DETAILS_EXCEL_PATH = os.path.join(EXCEL_DIR, "ilan_detaylari.xlsx")


def format_duration(seconds):
    if seconds < 0:
        return "0 dk 0 sn"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes} dk {seconds} sn"


def download_html_files():
    print("HTML dosyaları indiriliyor...")
    start_time = time.time()

    chromedriver_autoinstaller.install()
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    downloaded_files = []

    try:
        driver.get("https://www.milliemlak.gov.tr/#/")
        time.sleep(5)

        try:
            popup_close_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Close']"))
            )
            driver.execute_script("arguments[0].click();", popup_close_button)
            print("Pop-up kapatıldı.")
            time.sleep(2)
        except Exception:
            print("Pop-up bulunamadı.")

        satis_ilanlari_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//app-nav-bar-item[1]/div"))
        )
        driver.execute_script("arguments[0].click();", satis_ilanlari_button)

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//app-main-search-detail/form")
            )
        )
        time.sleep(5)

        ilan_ara_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'İLAN ARA')]")
            )
        )
        driver.execute_script("arguments[0].click();", ilan_ara_button)

        print("100 ilan göster seçiliyor...")
        try:
            per_page_dropdown = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//select[contains(@class, 'form-control')]")
                )
            )
            driver.execute_script(
                "arguments[0].value = '100'; arguments[0].dispatchEvent(new Event('change'));",
                per_page_dropdown,
            )
            time.sleep(5)
            print("100 ilan göster seçildi.")
        except Exception as e:
            print(f"100 ilan göster seçilemedi: {e}")

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[@id='liste']//div[contains(@class, 'col')]")
            )
        )

        last_page = 1
        page_links = driver.find_elements(
            By.XPATH, "//ngb-pagination//a[@class='page-link']"
        )
        for link in page_links:
            page_text = link.text.strip()
            if page_text.isdigit():
                last_page = max(last_page, int(page_text))

        page = 1
        while page <= last_page:
            print(f"Sayfa {page} indiriliyor...")
            wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//*[@id='liste']//div[contains(@class, 'col')]")
                )
            )
            html_content = driver.page_source
            html_file_name = f"milli{'' if page == 1 else page}.html"
            html_file_path = os.path.join(HTML_DIR, html_file_name)
            with open(html_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            downloaded_files.append(html_file_name)
            print(f"Kaydedildi: {html_file_path}")

            if page < last_page:
                next_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next']"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
            page += 1

    finally:
        driver.quit()

    elapsed_time = time.time() - start_time
    print(f"HTML indirme tamamlandı. Süre: {format_duration(elapsed_time)}")
    return downloaded_files


def extract_links(html_file_path):
    print(f"Linkler ve kategoriler çekiliyor: {html_file_path}")
    with open(html_file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    ilan_data = []
    seen_links = set()

    ilan_elements = soup.select("div.search-result a[href*='#/ilan-detay']")
    for element in ilan_elements:
        href = element.get("href")
        if href and "#/ilan-detay" in href:
            link_part = href.split("#/ilan-detay")[1]
            full_url = f"https://www.milliemlak.gov.tr/#/ilan-detay{link_part}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            kategori_label = element.find(
                "label", class_="box-label background-orange"
            )
            kategori = (
                kategori_label.text.strip() if kategori_label else "N/A"
            )

            ilan_data.append({"Link": full_url, "Kategori": kategori})

    if not ilan_data:
        print("Hiçbir ilan bulunamadı, HTML yapısı kontrol ediliyor...")
        print(soup.prettify()[:1000])

    return ilan_data


def save_to_excel(ilan_data, excel_file):
    df = pd.DataFrame(ilan_data, columns=["Link", "Kategori"])
    df.to_excel(excel_file, index=False)


def merge_excels(downloaded_files, merged_excel_path):
    print("Excel birleştirme başlıyor...")
    start_time = time.time()

    file_paths = [
        os.path.join(
            EXCEL_DIR, f"ilan_links_{downloaded_files.index(f) + 1}.xlsx"
        )
        for f in downloaded_files
    ]
    ilan_data_list = []

    for file in file_paths:
        if os.path.exists(file):
            df = pd.read_excel(file)
            ilan_data_list.append(df)

    if ilan_data_list:
        merged_df = pd.concat(ilan_data_list, ignore_index=True)
        merged_df.to_excel(merged_excel_path, index=False)
    else:
        pd.DataFrame(columns=["Link", "Kategori"]).to_excel(
            merged_excel_path, index=False
        )

    elapsed_time = time.time() - start_time
    print(f"Excel birleştirme tamamlandı. Süre: {format_duration(elapsed_time)}")
    print(f"Sonuç dosyası: {merged_excel_path}")


def extract_details(merged_excel_path, details_excel_path):
    print("Detay çekme başlıyor...")
    start_time = time.time()

    def turkce_to_ingilizce(text):
        if text == "N/A" or not isinstance(text, str):
            return text
        turkce_karakterler = "çğıöşüÇĞİÖŞÜ"
        ingilizce_karakterler = "cgiosuCGIOSU"
        for turkce, ingilizce in zip(turkce_karakterler, ingilizce_karakterler):
            text = text.replace(turkce, ingilizce)
        return text

    def get_lat_lng(driver, wait, link):
        try:
            button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='KONUMU GÖSTER']")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView();", button)
            driver.execute_script("arguments[0].click();", button)
            WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(2))
            all_windows = driver.window_handles
            driver.switch_to.window(all_windows[-1])
            current_url = driver.current_url
            match = re.search(r"q=([\d.-]+),([\d.-]+)", current_url)
            lat, lng = (match.group(1), match.group(2)) if match else ("", "")
            driver.close()
            driver.switch_to.window(all_windows[0])
            return lat, lng
        except Exception as e:
            print(f"Lat-Lng çekilirken hata (Link: {link}): {e}")
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            return "", ""

    df = pd.read_excel(merged_excel_path)
    links = df["Link"].tolist()
    kategoriler = df["Kategori"].tolist()
    total_links = len(links)
    print(f"Toplam {total_links} ilan bulunacak.")

    chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.page_load_strategy = "eager"
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    detay_data = []
    ilan_times = []

    def get_element_text(xpath):
        try:
            element = wait.until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element.text
        except Exception as e:
            print(f"Element bulunamadı (XPath: {xpath}): {e}")
            return ""

    try:
        for idx, link in enumerate(links):
            ilan_start_time = time.time()
            current_index = idx + 1
            print(f"İlan {current_index}/{total_links} işleniyor... (Link: {link})")

            elapsed_time = time.time() - start_time
            elapsed_time_str = format_duration(elapsed_time)

            if current_index > 1:
                recent_times = (
                    ilan_times[-5:] if len(ilan_times) >= 5 else ilan_times
                )
                avg_time_per_ilan = sum(recent_times) / len(recent_times)
                remaining_ilans = total_links - current_index
                estimated_remaining_time = avg_time_per_ilan * remaining_ilans
                estimated_remaining_time_str = format_duration(
                    estimated_remaining_time
                )
            else:
                estimated_remaining_time_str = "Hesaplanıyor..."

            print(
                f"Geçen süre: {elapsed_time_str}, Tahmini kalan süre: {estimated_remaining_time_str}"
            )

            driver.get("about:blank")
            driver.get(link)
            print(f"Sayfa yükleniyor: {link}")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            '//td[text()="Taşınmaz No"]/following-sibling::td',
                        )
                    )
                )
                print("Sayfa başarıyla yüklendi.")
            except Exception as e:
                print(f"Sayfa yüklenemedi (Link: {link}): {e}")
                err_html = os.path.join(LOGS_DIR, f"error_page_{current_index}.html")
                err_img = os.path.join(LOGS_DIR, f"error_page_{current_index}.png")
                with open(err_html, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                driver.save_screenshot(err_img)
                continue

            kategori = turkce_to_ingilizce(kategoriler[idx])
            tasinmaz_no = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="Taşınmaz No"]/following-sibling::td'
                )
            )
            tahmini_ihale_bedeli = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="Tahmin Edilen İhale Bedeli"]/following-sibling::td'
                )
            )
            teminat_bedeli = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="Teminat Bedeli"]/following-sibling::td'
                )
            )
            uygun_yuzolcumu = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="Uygun Yüzölçümü"]/following-sibling::td'
                )
            )
            ihale_tarihi = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="İhale Tarihi"]/following-sibling::td'
                )
            )
            ihale_saati = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="İhale Saati"]/following-sibling::td'
                )
            )
            ihale_yeri = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="İhale Yeri"]/following-sibling::td'
                )
            )
            iletisim_adresi = turkce_to_ingilizce(
                get_element_text(
                    "/html/body/app-root/app-advert-detail/div/div[1]/div[2]/div[4]/table/tbody/tr[7]/td[2]/span/a"
                )
            )
            telefon = turkce_to_ingilizce(
                get_element_text(
                    '//td[text()="Telefon / Dahili"]/following-sibling::td'
                )
            )
            pafta_ada_parsel_raw = turkce_to_ingilizce(
                get_element_text(
                    '//*[@id="pn_id_1_content"]/div/div/div[2]/table/tbody/tr[2]/td[2]'
                )
            )
            imar_durumu = turkce_to_ingilizce(
                get_element_text(
                    '//*[@id="pn_id_1_content"]/div/div/div[2]/table/tbody/tr[3]/td[2]'
                )
            )
            plan_fonksiyonu = turkce_to_ingilizce(
                get_element_text(
                    '//*[@id="pn_id_1_content"]/div/div/div[2]/table/tbody/tr[4]/td[2]'
                )
            )
            yasal_dayanak = turkce_to_ingilizce(
                get_element_text(
                    '//*[@id="pn_id_1_content"]/div/div/div[2]/table/tbody/tr[5]/td[2]'
                )
            )
            tasinmaz_yuzolcumu = turkce_to_ingilizce(
                get_element_text(
                    '//*[@id="pn_id_1_content"]/div/div/div[2]/table/tbody/tr[6]/td[2]'
                )
            )
            hazine_hissesi = turkce_to_ingilizce(
                get_element_text(
                    '//*[@id="pn_id_1_content"]/div/div/div[2]/table/tbody/tr[7]/td[2]'
                )
            )

            lat, lng = get_lat_lng(driver, wait, link)
            page_url = turkce_to_ingilizce(link)
            page_title = turkce_to_ingilizce(driver.title)

            location_info = turkce_to_ingilizce(
                get_element_text(
                    "/html/body/app-root/app-advert-detail/div/div[3]/div/p-accordion/div/p-accordiontab/div/div[1]/a/p-header/div/h5"
                )
            )
            if location_info:
                parts = location_info.split("/")
                if len(parts) >= 3:
                    il = parts[0].strip()
                    ilce = parts[1].strip()
                    mahalle_ada_parsel = "/".join(parts[2:]).strip()
                    if "/" in mahalle_ada_parsel:
                        mahalle_ada, parsel = mahalle_ada_parsel.rsplit("/", 1)
                        parsel = parsel.strip()
                    else:
                        mahalle_ada = mahalle_ada_parsel
                        parsel = ""
                    mahalle_parts = mahalle_ada.rsplit(" ", 1)
                    if (
                        len(mahalle_parts) > 1
                        and mahalle_parts[1].strip().isdigit()
                    ):
                        mahalle = mahalle_parts[0].strip()
                        ada = mahalle_parts[1].strip()
                    else:
                        mahalle = mahalle_ada.strip()
                        ada = ""
                else:
                    il = ilce = mahalle = ada = parsel = ""
            else:
                il = ilce = mahalle = ada = parsel = ""

            if pafta_ada_parsel_raw and "/" in pafta_ada_parsel_raw:
                pafta = pafta_ada_parsel_raw.split("/")[0].strip()
                pafta_ada_parsel = pafta_ada_parsel_raw
            else:
                pafta = ""
                pafta_ada_parsel = f"{ada}-{parsel}"

            detay_data.append(
                {
                    "page_url": page_url,
                    "kategori": kategori,
                    "tasinmaz_no": tasinmaz_no,
                    "tahmini_ihale_bedeli": tahmini_ihale_bedeli,
                    "teminat_bedeli": teminat_bedeli,
                    "uygun_yuzolcumu": uygun_yuzolcumu,
                    "satilacak_yuzolcumu": uygun_yuzolcumu,
                    "ihale_tarihi": ihale_tarihi,
                    "ihale_saati": ihale_saati,
                    "ihale_yeri": ihale_yeri,
                    "iletisim_adresi": iletisim_adresi,
                    "telefon": telefon,
                    "il": il,
                    "ilce": ilce,
                    "mahalle": mahalle,
                    "pafta": pafta,
                    "ada": ada,
                    "parsel": parsel,
                    "pafta_ada_parsel": pafta_ada_parsel,
                    "imar_durumu": imar_durumu,
                    "plan_fonksiyonu": plan_fonksiyonu,
                    "yasal_dayanak": yasal_dayanak,
                    "tasinmaz_yuzolcumu": tasinmaz_yuzolcumu,
                    "hazine_hissesi": hazine_hissesi,
                    "lat": lat,
                    "lng": lng,
                    "page_title": page_title,
                }
            )

            print(f"Çekilen veriler (İlan {current_index}):")
            print(f"Taşınmaz No: {tasinmaz_no}")
            print(f"Tahmini İhale Bedeli: {tahmini_ihale_bedeli}")
            print(f"Lat: {lat}, Lng: {lng}")
            print("-" * 50)

            ilan_end_time = time.time()
            ilan_times.append(ilan_end_time - ilan_start_time)

    finally:
        driver.quit()

    detay_df = pd.DataFrame(detay_data)
    detay_df = detay_df.rename(columns=turkce_to_ingilizce)
    detay_df = detay_df.replace("N/A", "")
    detay_df["spu"] = "python"
    detay_df.to_excel(details_excel_path, index=False)

    total_elapsed_time = time.time() - start_time
    print(f"Detay çekme tamamlandı. Süre: {format_duration(total_elapsed_time)}")
    print(f"Sonuç dosyası: {details_excel_path}")


def main():
    downloaded_files = download_html_files()

    print("1. Aşama: Link Çekme")
    start_time = time.time()
    for html_file in downloaded_files:
        print(f"Processing {html_file}...")
        ilan_data = extract_links(os.path.join(HTML_DIR, html_file))
        print(f"Toplam {len(ilan_data)} ilan bulundu ({html_file}).")
        excel_file = os.path.join(
            EXCEL_DIR, f"ilan_links_{downloaded_files.index(html_file) + 1}.xlsx"
        )
        save_to_excel(ilan_data, excel_file)
        print(f"Excel dosyası oluşturuldu: {excel_file}")
    print(
        f"1. Aşama tamamlandı. Süre: {format_duration(time.time() - start_time)}"
    )

    merge_excels(downloaded_files, MERGED_EXCEL_PATH)
    extract_details(MERGED_EXCEL_PATH, DETAILS_EXCEL_PATH)


if __name__ == "__main__":
    main()