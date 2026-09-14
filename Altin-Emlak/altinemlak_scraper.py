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

# .env dosyasından ortam değişkenlerini yükle
load_dotenv()

# Logging ayarları
logging.basicConfig(
    filename='scraper.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Veritabanı bağlantı bilgileri (Ortam değişkenlerinden alınır)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "your_db_name"),
    "user": os.getenv("DB_USER", "your_db_user"),
    "password": os.getenv("DB_PASSWORD", "your_db_password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "your_db_port")
}

# WebDriver başlatma
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

# Veritabanı bağlantısı
def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logging.info("Database connection established")
        return conn, cur
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        raise

# Pagination URL'lerini toplama
def get_pagination_urls(driver, wait, base_url):
    try:
        page_urls = [f"https://altinemlak.com.tr/portfoyler?Sorting=4&sayfa={i}" for i in range(1, 4)]
        logging.info(f"Collected {len(page_urls)} pagination URLs: {page_urls}")
        return page_urls
    except Exception as e:
        logging.error(f"Error getting pagination URLs: {str(e)}")
        return [base_url]

# İlan URL'lerini toplama
def scrape_page_listings(driver, wait, page_url):
    try:
        driver.get(page_url)
        time.sleep(random.uniform(0.5, 1.5))
        listing_urls = []
        for i in range(2, 12):
            xpath = f'//*[@id="filterForm"]/div/div[2]/div[1]/div[{i}]//a'
            try:
                listing = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                href = listing.get_attribute('href')
                if href:
                    listing_urls.append(href)
                    logging.debug(f"Collected listing URL: {href}")
            except Exception as e:
                logging.warning(f"Listing {i-1} not found on {page_url}: {str(e)}")
                continue
        logging.info(f"Scraped {len(listing_urls)} listing URLs from {page_url}")
        return listing_urls
    except Exception as e:
        logging.error(f"Error scraping listings from {page_url}: {str(e)}")
        return []

# İlan detaylarını çekme
def scrape_listing_details(driver, wait, url):
    try:
        driver.get(url)
        time.sleep(random.uniform(0.5, 1.5))
        data = {'page_url': url}

        # Ortak XPath'ler (tüm kategoriler için)
        common_xpaths = {
            'title': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[1]/div/h2',
            'portfolio_no': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[1]/div[1]/div/span/strong',
            'listing_date': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[1]/div[6]/p[1]',
            'location': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[1]/div/h2/span',
            'agent_name': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/a[2]/h4/span',
            'agent_office': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/a[1]/h4',
            'agent_license_no': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/h4[1]/span',
            'agent_phone': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/h4[2]/a/span',
            'agent_mobile': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/h4[3]/a/span',
            'agent_email': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/h4[4]/a/span',
            'agent_address': '//*[@id="main-wrapper"]/section[1]/div/div/div[2]/div/div/div[4]/div/div/h4[5]/span',
            'description': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[3]/div[2]',
        }

        # Değerlerin <li> içindeki metin node'larından alınacağı XPath'ler
        value_xpaths = {
            'property_type': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[1]',
            'floor': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[2]',
            'total_floors': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[3]',
            'room_count': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[4]',
            'heating': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[5]',
            'usage_status': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[6]',
            'bathroom_count': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[7]',
            'balcony': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[8]',
            'parcel': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[9]',
            'block': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[4]/div/ul/li[10]',
        }

        # Ortak alanları çek
        for key, xpath in common_xpaths.items():
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                if key == 'location':
                    location_text = element.text.strip()
                    try:
                        parts = location_text.split(', ')
                        if len(parts) == 3:
                            data['neighborhood'] = parts[0].strip()
                            data['district'] = parts[1].strip()
                            data['city'] = parts[2].strip()
                        else:
                            data['neighborhood'] = None
                            data['district'] = None
                            data['city'] = None
                            logging.warning(f"Invalid location format: {location_text} for {url}")
                    except Exception as e:
                        data['neighborhood'] = None
                        data['district'] = None
                        data['city'] = None
                        logging.warning(f"Error parsing location {location_text} for {url}: {str(e)}")
                else:
                    data[key] = element.text.strip()
                logging.debug(f"Scraped {key}: {data.get(key)} for {url}")
            except:
                data[key] = None
                logging.warning(f"Field {key} not found for {url}")

        # Değer alanlarını çek ve temizle
        for key, xpath in value_xpaths.items():
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                full_text = element.text.strip()
                label_element = element.find_element(By.XPATH, './strong')
                label_text = label_element.text.strip()
                value = full_text.replace(label_text, '').strip()
                data[key] = value
                logging.debug(f"Scraped {key}: {data[key]} for {url}")
            except:
                data[key] = None
                logging.warning(f"Field {key} not found for {url}")

        # Kategoriye göre resim XPath'leri
        category = None
        property_type = data.get('property_type', '').lower()
        if any(x in property_type for x in ['daire', 'villa', 'residence']):
            category = 'Konut'
            image_xpaths = {
                'image_1': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[7]/img',
                'image_2': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[8]/img',
                'image_3': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[9]/img',
            }
        elif any(x in property_type for x in ['arsa', 'arazi', 'bahçe']):
            category = 'Arsa'
            image_xpaths = {
                'image_1': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[1]/img',
                'image_2': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[2]/img',
                'image_3': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[3]/img',
            }
        else:
            category = 'Ticari'
            image_xpaths = {
                'image_1': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[7]/img',
                'image_2': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[8]/img',
                'image_3': '//*[@id="main-wrapper"]/section[1]/div/div/div[1]/div[2]/div[2]/div/div/div[9]/img',
            }
        data['category'] = category

        # Resimleri çek
        for key, xpath in image_xpaths.items():
            try:
                img = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                data[key] = img.get_attribute('src')
                logging.debug(f"Scraped {key}: {data[key]} for {url}")
            except:
                data[key] = None
                logging.warning(f"Image {key} not found for {url}")

        # Lat/lng çekme
        try:
            google_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="map"]/div[1]/div[3]/div[13]/div/a')))
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

        # İlan türü (Satılık/Kiralık)
        title = data.get('title', '').lower()
        data['listing_type'] = 'Kiralık' if 'kiralık' in title else 'Satılık'

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
            'title', 'portfolio_no', 'listing_date', 'neighborhood', 'district', 'city',
            'agent_name', 'agent_office', 'agent_license_no', 'agent_phone', 'agent_mobile', 'agent_email',
            'agent_address', 'description', 'property_type', 'floor', 'total_floors', 'room_count',
            'heating', 'usage_status', 'bathroom_count', 'balcony', 'parcel', 'block', 'category',
            'listing_type', 'lat', 'lng', 'image_1', 'image_2', 'image_3', 'page_url'
        ]
        for col in columns:
            if col not in data:
                data[col] = None
        logging.debug(f"Attempting to insert data: {data}")
        
        # Anonimleştirilmiş tablo adı: public.scraped_properties
        insert_query = sql.SQL("""
            INSERT INTO public.scraped_properties ({})
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
        base_url = 'https://altinemlak.com.tr/portfoyler?Sorting=4&sayfa=1'
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