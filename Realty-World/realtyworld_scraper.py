import os
import random
import time
import logging
import psycopg2
from psycopg2 import sql
import chromedriver_autoinstaller
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Çevre değişkenlerini (.env dosyasını) yükle
load_dotenv()

# Logging Yapılandırması
logging.basicConfig(
    filename='scraper_realtyworld.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Veritabanı Bağlantı Bilgileri (Çevre Değişkenlerinden Okunur)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "your_db_name"),
    "user": os.getenv("DB_USER", "your_db_user"),
    "password": os.getenv("DB_PASSWORD", "your_db_password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "your_db_port")
}

# Veritabanı Şema ve Tablo Bilgisi
SCHEMA_NAME = os.getenv("DB_SCHEMA", "public")
TABLE_NAME = os.getenv("DB_TABLE", "scrap_ad_realty")


# Selenium WebDriver İlklendirme
def init_driver():
    try:
        chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.page_load_strategy = 'normal'
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 7)
        logging.info("WebDriver initialized successfully")
        return driver, wait
    except Exception as e:
        logging.error(f"Error initializing WebDriver: {str(e)}")
        raise


# PostgreSQL Veritabanı Bağlantısı
def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logging.info("Database connection established")
        return conn, cur
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        raise


# Sayfa Üzerindeki İlan Linklerini Çekme
def scrape_page_listings(driver, wait, page_url):
    try:
        driver.get(page_url)
        time.sleep(random.uniform(0.5, 1.5))
        listing_urls = []
        for i in range(1, 13):  # Her sayfada 12 ilan
            xpath = f'//*[@id="portfoylist"]/div/div/div[1]/div/div[{i}]//a'
            try:
                listing = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                href = listing.get_attribute('href')
                if href:
                    listing_urls.append(href)
                    logging.debug(f"Collected listing URL: {href}")
            except Exception as e:
                logging.warning(f"Listing {i} not found on {page_url}: {str(e)}")
                continue
        logging.info(f"Scraped {len(listing_urls)} listing URLs from {page_url}")
        return listing_urls
    except Exception as e:
        logging.error(f"Error scraping listings from {page_url}: {str(e)}")
        return []


# Sayfalandırma (Pagination) URL'lerini Alma
def get_pagination_urls(driver, wait, base_url):
    try:
        driver.get(base_url)
        time.sleep(random.uniform(0.5, 1.5))

        # Kategori filtresini kaldır
        x_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="select2-propertytype-container"]/span')))
        x_button.click()
        logging.debug("Clicked 'x' button to remove category filter")
        time.sleep(random.uniform(0.3, 0.7))

        # Arama butonuna tıkla
        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="searchForm"]/div[10]/button')))
        search_button.click()
        logging.debug("Clicked search button")
        time.sleep(random.uniform(0.5, 1.5))

        # İlk 3 sayfa için URL üret
        page_urls = [f"https://www.realtyworld.com.tr/tr/portfoyler?Page_No={i}" for i in range(1, 4)]
        logging.info(f"Generated {len(page_urls)} pagination URLs: {page_urls}")
        return page_urls
    except Exception as e:
        logging.error(f"Error getting pagination URLs: {str(e)}")
        return [base_url]


# İlan Detaylarını Kazıma
def scrape_listing_details(driver, wait, url):
    try:
        driver.get(url)
        time.sleep(random.uniform(0.5, 1.5))
        data = {'page_url': url}

        # Genel alanlar
        common_xpaths = {
            'title': '//*[@id="page"]/div[2]/section/div[1]/div[1]/h1',
            'address': '//*[@id="page"]/div[2]/section/div[1]/div[2]/div[1]/address',
            'description': '//*[@id="page"]/div[2]/section/div[2]/div/div/div[1]/div/div[4]/div[2]',
            'description_alt': '//*[@id="page"]/div[2]/section/div[2]/div/div/div[1]/div/div[4]/div[2]/p',
            'agent_name': '//*[@id="agentinfo"]/div/div[1]/aside/div/h3',
            'agent_office': '//*[@id="agentinfo"]/div/div[1]/aside/div/p/a',
            'agent_phone': '//*[@id="agentinfo"]/div/div[1]/aside/div/dl/dd[1]',
            'agent_mobile': '//*[@id="agentinfo"]/div/div[1]/aside/div/dl/dd[2]',
            'agent_email': '//*[@id="agentinfo"]/div/div[1]/aside/div/dl/dd[3]/a',
            'agent_address': '//*[@id="agentinfo"]/div/div[1]/aside/div/dl/dd[4]',
        }

        for key, xpath in common_xpaths.items():
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                data[key] = element.text.strip()
                if key == 'description' and not data[key]:
                    try:
                        element = wait.until(EC.presence_of_element_located((By.XPATH, common_xpaths['description_alt'])))
                        data[key] = element.text.strip()
                    except:
                        data[key] = None
                logging.debug(f"Scraped {key}: {data[key]} for {url}")
            except:
                data[key] = None
                logging.warning(f"Field {key} not found for {url}")

        # Dinamik Tablo Eşleştirmeleri
        field_mappings = {
            'İlan No': 'listing_no',
            'İlan Giriş Tarihi': 'listing_date',
            'Güncelleme Tarihi': 'update_date',
            'Fiyat': 'price',
            'Metrekare': 'area',
            'İşlem Tipi': 'listing_type',
            'Gayrimenkul Tipi': 'property_type',
            'Tapu Durumu': 'title_status',
            'Kat Karşılığı Verilir': 'kat_karsiligi',
            'İmar Durumu': 'imar_durumu',
            'Alt Yapı': 'alt_yapi',
            'Genel Özellik': 'genel_ozellik',
            'Manzara': 'manzara',
            'Konum': 'konum',
            'Oda Sayısı': 'room_count',
            'Banyo Sayısı': 'bathroom_count',
            'Bina Yaşı': 'building_age',
            'Isıtma': 'heating',
            'Kredi Olanağı': 'credit_eligible',
            'Bölüm Sayısı': 'section_count',
        }

        dt_elements = driver.find_elements(By.XPATH, '//*[@id="page"]/div[2]/section/div[2]/div/div/div[1]/div/div[3]/div/dl/dt')
        dd_elements = driver.find_elements(By.XPATH, '//*[@id="page"]/div[2]/section/div[2]/div/div/div[1]/div/div[3]/div/dl/dd')

        for dt, dd in zip(dt_elements, dd_elements):
            try:
                label = dt.text.strip()
                value = dd.text.strip()
                for key, field in field_mappings.items():
                    if key.lower() in label.lower():
                        data[field] = value
                        logging.debug(f"Scraped {field}: {value} for {url}")
                        break
            except Exception as e:
                logging.warning(f"Error processing dt/dd pair for {url}: {str(e)}")
                continue

        category = data.get('property_type', '').lower()
        if 'arsa' in category:
            data['category'] = 'Arsa'
        elif 'konut' in category or 'daire' in category or 'villa' in category:
            data['category'] = 'Konut'
        else:
            data['category'] = 'İşyeri'

        # Lat / Lng koordinatlarını al
        try:
            google_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="property-detail-map"]/div/div[3]/div[13]/div/a')))
            href = google_link.get_attribute('href')
            logging.debug(f"Google link href: {href} for {url}")
            if href and 'll=' in href:
                ll_part = href.split('ll=')[1].split('&')[0]
                lat, lng = ll_part.split(',')
                data['lat'] = lat
                data['lng'] = lng
                logging.debug(f"Scraped lat: {lat}, lng: {lng} for {url}")
            else:
                data['lat'], data['lng'] = None, None
                logging.warning(f"No valid lat/lng found in href: {href} for {url}")
        except Exception as e:
            data['lat'], data['lng'] = None, None
            logging.warning(f"Error scraping lat/lng for {url}: {str(e)}")

        # Görselleri al (3 adede kadar)
        for i in range(1, 4):
            try:
                img = wait.until(EC.presence_of_element_located((By.XPATH, f'//*[@id="page"]/div[2]/section/div[2]/div/div/div[1]/div/div[1]/div[2]/ul/div[1]/div/div[{i}]/li/div/figure/img')))
                data[f'image_{i}'] = img.get_attribute('src')
                logging.debug(f"Scraped image_{i}: {data[f'image_{i}']} for {url}")
            except:
                data[f'image_{i}'] = None
                logging.warning(f"Image {i} not found for {url}")

        logging.info(f"Scraped details for {url}: {data}")
        return data
    except Exception as e:
        logging.error(f"Error scraping details for {url}: {str(e)}")
        return None


# Verileri PostgreSQL Veritabanına Kaydetme
def save_to_db(conn, cur, data):
    if not data or not data.get('listing_no'):
        logging.warning(f"Skipping save for data with no listing_no: {data}")
        return
    try:
        columns = [
            'title', 'address', 'description', 'agent_name', 'agent_office', 'agent_phone',
            'agent_mobile', 'agent_email', 'agent_address', 'listing_no', 'listing_date',
            'update_date', 'price', 'area', 'listing_type', 'category', 'title_status',
            'kat_karsiligi', 'imar_durumu', 'alt_yapi', 'genel_ozellik', 'manzara', 'konum',
            'room_count', 'bathroom_count', 'building_age', 'heating', 'credit_eligible',
            'section_count', 'lat', 'lng', 'image_1', 'image_2', 'image_3', 'page_url'
        ]
        for col in columns:
            if col not in data:
                data[col] = None
        logging.debug(f"Attempting to insert data: {data}")

        # Dinamik şema ve tablo ismi kullanımı
        table_identifier = sql.Identifier(SCHEMA_NAME, TABLE_NAME)

        insert_query = sql.SQL("""
            INSERT INTO {} ({})
            VALUES ({})
            ON CONFLICT (listing_no) DO NOTHING
        """).format(
            table_identifier,
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )
        cur.execute(insert_query, [data[col] for col in columns])
        conn.commit()
        logging.info(f"Saved data for listing_no: {data.get('listing_no')}")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error saving data to database: {str(e)}")
        logging.error(f"Failed data: {data}")
        raise


def main():
    driver, wait = None, None
    conn, cur = None, None
    try:
        driver, wait = init_driver()
        conn, cur = init_db()
        base_url = 'https://www.realtyworld.com.tr/tr/portfoyler?Page_No=1'
        page_urls = get_pagination_urls(driver, wait, base_url)
        for page_url in page_urls:
            listing_urls = scrape_page_listings(driver, wait, page_url)
            for url in listing_urls:
                data = scrape_listing_details(driver, wait, url)
                save_to_db(conn, cur, data)
                time.sleep(random.uniform(0.5, 1.5))
        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Main loop error: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver closed")
        if conn:
            cur.close()
            conn.close()
            logging.info("Database connection closed")


if __name__ == "__main__":
    main()