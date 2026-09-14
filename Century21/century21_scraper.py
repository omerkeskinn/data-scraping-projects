import os
import time
import random
import logging
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import psycopg2
from psycopg2 import sql
import chromedriver_autoinstaller

# Ortam değişkenlerini (.env dosyasını) yükle
load_dotenv()

# Logging ayarları
logging.basicConfig(
    filename='scraper.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Veritabanı bağlantı bilgileri (Güvenlik amacıyla ortam değişkenlerinden okunur)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "your_db_name"),
    "user": os.getenv("DB_USER", "your_db_user"),
    "password": os.getenv("DB_PASSWORD", "your_db_password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "your_db_port")
}

# Selenium WebDriver başlatma
def init_driver():
    try:
        chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.page_load_strategy = 'normal'
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 7)
        logging.info("WebDriver initialized successfully")
        return driver, wait
    except Exception as e:
        logging.error(f"Error initializing WebDriver: {str(e)}")
        raise

# PostgreSQL bağlantısı
def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logging.info("Database connection established")
        return conn, cur
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        raise

# Tek sayfadaki ilan linklerini toplama
def scrape_page_listings(driver, wait, page_url):
    try:
        driver.get(page_url)
        time.sleep(random.uniform(0.5, 1.5))
        listing_urls = []
        for i in range(1, 11):
            xpath = f'/html/body/section[2]/div/div[2]/div[1]/div[1]/div[{i}]//a'
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

# Sayfalama (Pagination) linklerini alma
def get_pagination_urls(driver, wait, base_url):
    try:
        driver.get(base_url)
        arayin_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="sb-mc-01-btn"]')))
        arayin_button.click()
        time.sleep(random.uniform(0.5, 1.5))
        sort_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="dropdownMenuOffset"]')))
        sort_button.click()
        time.sleep(random.uniform(0.3, 0.7))
        sort_by_date = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="sortByCreateDate"]')))
        sort_by_date.click()
        time.sleep(random.uniform(0.5, 1.5))

        pagination_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//ul[@class="pagination"]/li/a')))
        page_urls = list(dict.fromkeys([link.get_attribute('href') for link in pagination_links if link.get_attribute('href')]))[:3]
        if not page_urls:
            page_urls = [driver.current_url]
        logging.info(f"Collected {len(page_urls)} pagination URLs: {page_urls}")
        return page_urls
    except Exception as e:
        logging.error(f"Error getting pagination URLs: {str(e)}")
        return [driver.current_url]

# İlan detaylarını çekme
def scrape_listing_details(driver, wait, url):
    try:
        driver.get(url)
        time.sleep(random.uniform(0.5, 1.5))
        data = {'page_url': url}

        common_xpaths = {
            'title': '/html/body/section[1]/div[1]/div/div[2]/div/div/h3',
            'portfolio_no': '/html/body/section[1]/div[1]/div/div[1]/div/div/div//div[@class="feature-item"]',
            'agent_name': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[1]',
            'agent_office': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[2]',
            'agent_email': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[3]',
            'agent_phone': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/ul[2]/li/a',
        }

        for key, xpath in common_xpaths.items():
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                if key == 'portfolio_no':
                    text = element.text.strip()
                    data[key] = text.replace('Portföy No:', '').strip()
                else:
                    data[key] = element.text.strip()
                logging.debug(f"Scraped {key}: {data[key]} for {url}")
            except:
                data[key] = None
                logging.warning(f"Field {key} not found for {url}")

        table_rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, '/html/body/section[2]/div/div/div[1]/div[3]/div[2]/div/div[1]/div/table/tbody/tr')))
        field_mappings = {
            'Konum': 'location',
            'Tapu Durumu': 'title_status',
            'Kategori': 'category',
            'Fiyat': 'price',
            'Metre Kare (Net)': 'area_net',
            'Net m²': 'area_net',
            'Metre Kare (Brüt)': 'area_gross',
            'Brüt m²': 'area_gross',
            'Oda Sayısı': 'room_count',
            'Bina Yaşı': 'building_age',
            'Bulunduğu Kat': 'floor',
            'Kat Sayısı': 'total_floors',
            'Isıtma': 'heating',
            'Banyo Sayısı': 'bathroom_count',
            'Balkon': 'balcony',
            'Eşyalı': 'furnished',
            'Kullanım Durumu': 'usage_status',
            'Aidat': 'dues',
            'Depozito': 'deposit',
            'Krediye Uygun': 'credit_eligible',
            'Takaslı': 'trade_eligible',
            'İmar Durumu': 'zoning_status',
            'Kaks (Emsal)': 'kaks',
            'Site İçerisinde': 'in_site',
        }

        for row in table_rows:
            try:
                label = row.find_element(By.XPATH, './td[1]').text.strip()
                value = row.find_element(By.XPATH, './td[2]').text.strip()
                for key, field in field_mappings.items():
                    if key.lower() in label.lower():
                        data[field] = value
                        logging.debug(f"Scraped {field}: {value} for {url}")
                        break
            except Exception as e:
                logging.warning(f"Error processing table row for {url}: {str(e)}")
                continue

        category = data.get('category')
        if category in ['Konut İmarlı', 'Arsa']:
            category = 'Arsa'
        elif category in ['Daire', 'Villa', 'Residence']:
            category = 'Konut'
        elif category in ['Dükkan / Mağaza', 'Ofis', 'Depo']:
            category = 'Ticari'
        elif category in ['Devremülk', 'Otel', 'Pansiyon']:
            category = 'Turizm'
        data['category'] = category

        # Haritadan enlem/boylam (lat/lng) bilgisi alma
        try:
            map_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="showMapButton"]')))
            map_button.click()
            logging.debug(f"Clicked map button for {url}")
            time.sleep(random.uniform(0.5, 1.5))

            google_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="map-canvas"]/div/div[3]/div[13]/div/a')))
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

        price = data.get('price', '')
        data['listing_type'] = 'Kiralık' if 'Kiralık' in data.get('title', '') or 'kira' in price.lower() else 'Satılık'

        for i in range(1, 4):
            try:
                img = wait.until(EC.presence_of_element_located((By.XPATH, f'//*[@id="cb-item-gallery"]/ol/li[{i}]/img')))
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

# Veritabanına kaydetme
def save_to_db(conn, cur, data):
    if not data or not data.get('portfolio_no'):
        logging.warning(f"Skipping save for data with no portfolio_no: {data}")
        return
    try:
        columns = [
            'title', 'portfolio_no', 'agent_name', 'agent_office', 'agent_email', 'agent_phone',
            'location', 'title_status', 'category', 'listing_type', 'price', 'area_net',
            'area_gross', 'room_count', 'building_age', 'floor', 'total_floors', 'heating',
            'bathroom_count', 'balcony', 'furnished', 'usage_status', 'dues', 'deposit',
            'credit_eligible', 'trade_eligible', 'zoning_status', 'kaks',
            'in_site', 'lat', 'lng', 'image_1', 'image_2', 'image_3', 'page_url'
        ]
        for col in columns:
            if col not in data:
                data[col] = None
        logging.debug(f"Attempting to insert data: {data}")
        
        # Genel tablo ismi kullanıldı: public.real_estate_listings
        insert_query = sql.SQL("""
            INSERT INTO public.real_estate_listings ({})
            VALUES ({})
            ON CONFLICT (portfolio_no) DO NOTHING
        """).format(
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )
        cur.execute(insert_query, [data[col] for col in columns])
        conn.commit()
        logging.info(f"Saved data for portfolio_no: {data.get('portfolio_no')}")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error saving data to database: {str(e)}")
        logging.error(f"Failed data: {data}")
        raise

# Ana fonksiyon
def main():
    driver, wait = None, None
    conn, cur = None, None
    try:
        driver, wait = init_driver()
        conn, cur = init_db()
        base_url = 'https://www.century21.com.tr'
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