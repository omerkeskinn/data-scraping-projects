import asyncio
import aiohttp
from lxml import html
import json
import re
import time
import os
from playwright.async_api import async_playwright
import psycopg2
from psycopg2 import sql
from datetime import datetime
from dotenv import load_dotenv

# Environment değişkenlerini yükle
load_dotenv()

# --- SABİTLER ---
BASE_URL = "https://www.guncelprojebilgileri.com"
SEARCH_URL = BASE_URL + "/search?min_tutar=&max_tutar=&city=&area=&sayfa=1"

HEADERS = {"User-Agent": "Mozilla/5.0"}
XPATH_BLOCKS = [
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[1]',
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[3]',
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[4]',
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[6]',
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[7]',
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[8]',
    '//*[@id="main-wrapper"]/section/div/div/div[2]/div[9]',
    '//*[@id="main-wrapper"]/section/div/div/div[3]/div/div[3]',
]
IMG_XPATH = '//*[@id="photostab"]//a/@href'
MAPS_REGEX = r"ll=([-]?\d+\.\d+),([-]?\d+\.\d+)"

# --- VERİTABANI KONFİGÜRASYONU ---
DB_NAME = os.getenv("DB_NAME", "your_db_name")
DB_USER = os.getenv("DB_USER", "your_db_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_db_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "your_db_port")
DB_TABLE = os.getenv("DB_TABLE", "public.projects")


# --- Yardımcı fonksiyonlar ---

def clean_text(text):
    return ' '.join(text.strip().split())


def parse_content_list(content_list, tree):
    result = {}
    current_section = None
    section_titles = {
        "Proje Bilgileri",
        "Site Özellikleri",
        "Bina Özellikleri",
        "Konut Özellikleri",
        "İnşaat Teknikleri",
        "İletişim Bilgileri",
        "Editörün Yorumu",
        "Ödeme Seçenekleri",
        "Proje Hakkında"
    }
    list_sections = {
        "Site Özellikleri",
        "Bina Özellikleri",
        "Konut Özellikleri",
        "İnşaat Teknikleri"
    }
    keyval_sections = {
        "Proje Bilgileri",
        "İletişim Bilgileri"
    }
    multiline_sections = {
        "Proje Hakkında",
        "Ödeme Seçenekleri"
    }

    last_key = None
    expect_value = False

    for line in content_list:
        if line in section_titles:
            current_section = line
            if current_section in list_sections:
                result[current_section] = []
            elif current_section in keyval_sections:
                result[current_section] = {}
            elif current_section in multiline_sections:
                result[current_section] = []
            else:
                result[current_section] = {}
            expect_value = False
            last_key = None
            continue

        if not current_section:
            continue

        if current_section in list_sections:
            result[current_section].append(line)
        elif current_section in keyval_sections:
            if not expect_value:
                last_key = line
                expect_value = True
            else:
                result[current_section][last_key] = line
                expect_value = False
        elif current_section in multiline_sections:
            result[current_section].append(line)
        else:
            if not expect_value:
                last_key = line
                expect_value = True
            else:
                result[current_section][last_key] = line
                expect_value = False

    mail_onclicks = tree.xpath(
        '//*[@id="main-wrapper"]//div[contains(@class,"cn-info-detail")]//a[contains(@onclick,"gpbClick")]/@onclick')
    for onclick_text in mail_onclicks:
        match = re.search(r"gpbClick\('Mail','.*?','(.*?)'\);", onclick_text)
        if match:
            mail_adres = match.group(1)
            if "İletişim Bilgileri" not in result:
                result["İletişim Bilgileri"] = {}
            result["İletişim Bilgileri"]["Mail"] = mail_adres
            break

    return result


# --- Veritabanı işlemleri ---

def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Veritabanına bağlanıldı.")
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None


def insert_to_db(conn, data):
    cursor = conn.cursor()
    current_date = datetime.now().strftime("%Y-%m-%d")

    for url, details in data.items():
        try:
            print(f"Processing URL: {url}")
            location = details.get("Konum", "")
            city, district = "", ""
            if location and "/" in location:
                city, district = [part.strip() for part in location.split("/", 1)]

            proje_bilgileri = details.get("Proje Bilgileri", {})
            yapimci_firma = str(f"Yapımcı Firma\n{proje_bilgileri.get('Yapımcı Firma', '')}")
            proje_tipi = str(f"Proje Tipi\n{proje_bilgileri.get('Proje Tipi', '')}")
            konut_sayisi = str(f"Konut Sayısı\n{proje_bilgileri.get('Konut Sayısı', '')}")
            arsa_alani = str(f"Arsa Alanı\n{proje_bilgileri.get('Arsa Alanı', '')}")
            konut_tipleri = str(f"Konut Tipleri\n{proje_bilgileri.get('Konut Tipleri', '')}")
            metrekare_alani = str(f"Metrekare Alanı\n{proje_bilgileri.get('Metrekare Alanı', '')}")
            teslim_tarihi = str(f"Teslim Tarihi\n{proje_bilgileri.get('Teslim Tarihi', '')}")
            satis_durumu = str(f"Satış Durumu\n{proje_bilgileri.get('Satış Durumu', '')}")

            proje_hakkinda = details.get("Proje Hakkında", [])
            editor_yorumu = details.get("Editörün Yorumu", {})
            aciklama = str(next((line for line in proje_hakkinda
                               if not line.startswith(("Daire Tipi", "Fiyat Aralığı"))
                               and not re.match(r"^\d+\.\d+\.\d+", line)
                               and not line.endswith("TL")), ""))

            fiyat_lines = [line for line in proje_hakkinda
                           if line.startswith("Fiyat Aralığı") or line.endswith("TL")]
            editor_fiyat = ""
            if isinstance(editor_yorumu, dict):
                for key, value in editor_yorumu.items():
                    if key and ("en düşük" in key.lower() or "fiyat" in key.lower()):
                        editor_fiyat = str(value) if value is not None else ""
                        break
            fiyat = str("\n".join(fiyat_lines) if fiyat_lines else editor_fiyat)

            tip_lines = []
            for i, line in enumerate(proje_hakkinda):
                if line == "Daire Tipi" and i + 1 < len(proje_hakkinda):
                    next_line = proje_hakkinda[i + 1]
                    if re.match(r"^\d\+[0-2](,\s*\d\+[0-2])*$", next_line):
                        tip_lines = ["Daire Tipi", next_line]
                    break
            tip = str("\n".join(tip_lines) if tip_lines else proje_bilgileri.get("Konut Tipleri", ""))
            if tip == "Metrekare Alanı" or not tip:
                tip = ""

            odeme_durumu = str(details.get("Ödeme Seçenekleri", [""])[0])

            yorum_lines = []
            if isinstance(editor_yorumu, dict):
                for key, value in editor_yorumu.items():
                    if key is not None and value is not None:
                        try:
                            yorum_lines.append(f"{str(key).strip()}: {str(value).strip()}")
                        except (TypeError, ValueError) as e:
                            print(f"Yorum işleme hatası ({url}, key: {key}, value: {value}): {e}")
                            continue
            elif isinstance(editor_yorumu, list):
                for item in editor_yorumu:
                    if item and isinstance(item, str):
                        yorum_lines.append(item.strip())
            yorum = str("\n".join(yorum_lines)) if yorum_lines else ""

            ozellikler = str(",".join(details.get("Site Özellikleri", [])) if details.get("Site Özellikleri", []) else "")
            bina = str(",".join(details.get("Bina Özellikleri", [])) if details.get("Bina Özellikleri", []) else "")
            konut = str(",".join(details.get("Konut Özellikleri", [])) if details.get("Konut Özellikleri", []) else "")
            teknik = str(",".join(details.get("İnşaat Teknikleri", [])) if details.get("İnşaat Teknikleri", []) else "")

            iletisim = details.get("İletişim Bilgileri", {})
            tel = str(iletisim.get("Telefon", ""))
            mail = str(iletisim.get("Mail", ""))
            www = str(iletisim.get("Web Sitesi", ""))
            adres = str(iletisim.get("Adres", ""))

            photos = details.get("Fotoğraflar", [])
            images = (photos + [""] * (8 - len(photos)))[:8]

            values = (
                str("Anasayfa"), city, district, details.get("Başlık", ""), details.get("Başlık", ""),
                details.get("Durum", ""), url, yapimci_firma, proje_tipi, konut_sayisi,
                arsa_alani, konut_tipleri, metrekare_alani, teslim_tarihi, satis_durumu,
                aciklama, fiyat, tip, odeme_durumu, yorum,
                proje_bilgileri.get("Proje Tipi", ""), ozellikler, proje_bilgileri.get("Proje Tipi", ""),
                bina, konut, teknik, tel, mail, www, adres,
                str(details.get("Lng", "")), str(details.get("Lat", "")), url, details.get("Başlık", ""),
                BASE_URL + "/", current_date, current_date,
                str(images[0]), str(images[1]), str(images[2]), str(images[3]),
                str(images[4]), str(images[5]), str(images[6]), str(images[7])
            )

            if len(values) != 45:
                print(f"Hata: {url} için values uzunluğu {len(values)}, beklenen 45")
                continue

            columns = [
                'f1', 'f2', 'f3', 'f4', 'ad', 'title', 'url', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8',
                'aciklama', 'fiyat', 'tip', 'odeme_durumu', 'yorum', 'Field 1', 'ozellikler',
                'proje', 'bina', 'konut', 'teknik', 'tel', 'mail', 'www', 'adres', 'lng', 'lat',
                'page_url', 'page_title', 'spu', 'date_time', 'rec_date', 'image', 'image2',
                'image3', 'image4', 'image5', 'image6', 'image7', 'image8'
            ]

            table_parts = DB_TABLE.split('.')
            if len(table_parts) == 2:
                table_identifier = sql.Identifier(table_parts[0], table_parts[1])
            else:
                table_identifier = sql.Identifier(DB_TABLE)

            query = sql.SQL("""
                INSERT INTO {} ({})
                VALUES ({})
            """).format(
                table_identifier,
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns))
            )

            cursor.execute(query, values)
            conn.commit()
            print(f"Veri eklendi: {url}")
        except Exception as e:
            print(f"Veritabanına ekleme hatası ({url}): {e}")
            conn.rollback()
            continue
    print("Veriler veritabanına başarıyla eklendi.")
    cursor.close()


# --- İlan linklerini çekme fonksiyonları ---

async def fetch(session, url):
    async with session.get(url, headers=HEADERS) as response:
        return await response.text()


def get_listing_links_from_page(tree):
    listings = []
    container = tree.xpath('//*[@id="main-wrapper"]/section/div/div[2]/div[1]/div[1]')
    if not container:
        return listings
    container = container[0]
    ilan_divs = container.xpath('./div')
    for ilan in ilan_divs:
        hrefs = ilan.xpath('.//a[@href]/@href')
        for href in hrefs:
            if href and not href.startswith("http") and "konut-projeleri" in href:
                full_url = BASE_URL + "/" + href.lstrip("/")
                listings.append(full_url)
                break
    return listings


async def get_listing_urls(session, page_number):
    url = BASE_URL + f"/search?min_tutar=&max_tutar=&city=&area=&sayfa={page_number}"
    for attempt in range(3):
        try:
            page_content = await fetch(session, url)
            tree = html.fromstring(page_content)
            listings = get_listing_links_from_page(tree)
            if listings:
                return listings
            else:
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Hata sayfa {page_number} için: {e}")
            await asyncio.sleep(1)
    return []


async def get_all_listing_urls():
    async with aiohttp.ClientSession() as session:
        print("İlk sayfa için ilanlar çekiliyor...")
        listings = await get_listing_urls(session, 1)
        if not listings:
            print("!!! İlk sayfa boş ilan içeriyor veya veri alınamadı.")
        else:
            print(f"İlk sayfa için {len(listings)} ilan bulundu.")
        all_listings = sorted(listings)[:10]
        print(f"Test için toplam {len(all_listings)} benzersiz ilan seçildi.")
        return all_listings


# --- Ana scraping fonksiyonları ---

async def fetch_project(session, url):
    print(f"🚀 Başlıyor: {url}")
    async with session.get(url, headers=HEADERS) as response:
        html_text = await response.text()
        tree = html.fromstring(html_text)

        title = tree.xpath('//*[@id="main-wrapper"]/section/div/div/div[2]/div[1]/div/h1/text()')
        status = tree.xpath('//*[@id="main-wrapper"]/section/div/div/div[2]/div[1]/div/h3/text()')
        location = tree.xpath('//*[@id="main-wrapper"]/section/div/div/div[2]/div[1]/div/span/text()')

        title = title[0].strip() if title else ""
        status = status[0].strip() if status else ""
        location = location[0].strip() if location else ""

        content_list = []
        for xpath in XPATH_BLOCKS:
            block = tree.xpath(xpath)
            if block:
                texts = block[0].xpath('.//text()')
                for t in texts:
                    cleaned = clean_text(t)
                    if len(cleaned) > 1:
                        content_list.append(cleaned)

        details = parse_content_list(content_list, tree)

        photos = tree.xpath(IMG_XPATH)
        photos = [p.strip() for p in photos if p.strip() != ""]
        photos = photos[:10]

        details["Fotoğraflar"] = photos
        details["Başlık"] = title
        details["Durum"] = status
        details["Konum"] = location

        print(f"✅ aiohttp verisi alındı: {url} -> {len(photos)} fotoğraf")
        return url, details


async def fetch_lat_lng(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            lat_lng = await page.evaluate(
                """() => {
                    const mapDiv = document.querySelector('#singleMap');
                    if (mapDiv) {
                        return {
                            lat: mapDiv.getAttribute('data-latitude'),
                            lng: mapDiv.getAttribute('data-longitude')
                        };
                    }
                    return null;
                }"""
            )
            lat, lng = None, None
            if lat_lng and lat_lng['lat'] and lat_lng['lng']:
                lat, lng = lat_lng['lat'], lat_lng['lng']
            else:
                map_link = await page.evaluate(
                    """() => {
                        const link = document.querySelector('#singleMap a[href*="maps.google.com"]');
                        return link ? link.getAttribute('href') : null;
                    }"""
                )
                if map_link:
                    match = re.search(MAPS_REGEX, map_link)
                    if match:
                        lat, lng = match.groups()
            await browser.close()
            return {"Lat": lat, "Lng": lng}
    except Exception as e:
        print(f"❌ LatLng fetch error for {url}: {e}")
        return {"Lat": None, "Lng": None}


# --- Ana fonksiyon ---

async def main():
    start = time.time()
    results = {}

    listing_urls = await get_all_listing_urls()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_project(session, url) for url in listing_urls]
        aiohttp_results = await asyncio.gather(*tasks)

    lat_lng_tasks = [fetch_lat_lng(url) for url in listing_urls]
    lat_lng_results = await asyncio.gather(*lat_lng_tasks)

    for (url, details), latlng in zip(aiohttp_results, lat_lng_results):
        details["Lat"] = latlng.get("Lat")
        details["Lng"] = latlng.get("Lng")
        results[url] = details

    conn = connect_to_db()
    if conn:
        insert_to_db(conn, results)
        conn.close()
    else:
        print("Veritabanına bağlanılamadı, veri kaydedilemedi.")

    duration = time.time() - start
    print(f"⏱️ Tüm scraping işlemi tamamlandı. Süre: {duration:.2f} saniye")

    result_list = [{url: data} for url, data in results.items()]
    output_path = os.path.join(os.getcwd(), "output.json")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(result_list, ensure_ascii=False, indent=2))

    for url, data in results.items():
        print(f"{url} => {len(data.get('Fotoğraflar', []))} fotoğraf, Lat: {data.get('Lat')}, Lng: {data.get('Lng')}")


if __name__ == "__main__":
    asyncio.run(main())