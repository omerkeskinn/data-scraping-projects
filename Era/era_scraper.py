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

# Environment değişkenlerini yükle
load_dotenv()

# Logging yapılandırması
logging.basicConfig(
    filename='scraper_era.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Environment değişkenlerinden DB bilgilerini al
DB_NAME = os.getenv("DB_NAME", "your_db_name")
DB_USER = os.getenv("DB_USER", "your_db_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_db_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "your_db_port")
DB_TABLE = os.getenv("DB_TABLE", "public.real_estate_listings")


def init_driver():
    try:
        chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.page_load_strategy = 'normal'
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 7)
        logging.info("WebDriver successfully initialized.")
        return driver, wait
    except Exception as e:
        logging.error(f"Error initializing WebDriver: {str(e)}")
        raise


def init_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        logging.info("Database connection established.")
        return conn, cur
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        raise


def get_pagination_urls(driver, wait, base_url):
    try:
        page_urls = [f"{base_url.replace('pager_p=1', f'pager_p={i}')}" for i in range(1, 4)]
        logging.info(f"Generated {len(page_urls)} pagination URLs: {page_urls}")
        return page_urls
    except Exception as e:
        logging.error(f"Error generating pagination URLs: {str(e)}")
        return [base_url]


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


def scrape_listing_details(driver, wait, url):
    try:
        driver.get(url)
        time.sleep(random.uniform(0.5, 1.5))
        data = {'page_url': url}

        common_xpaths = {
            'title': '/html/body/section[1]/div[1]/div/div[2]/div/div/h3',
            'portfolio_no': '/html/body/section[1]/div[1]/div/div[1]/div/div/div/div/div',
            'agent_name': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[1]',
            'agent_office': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[2]',
            'agent_email': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/a[3]',
            'agent_phone': '/html/body/section[2]/div/div/div[2]/div/div[1]/div[2]/ul[2]/li/a',
            'description': '/html/body/section[2]/div/div/div[1]/div[2]/div[2]'
        }

        for key, xpath in common_xpaths.items():
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                data[key] = element.text.strip()
                logging.debug(f"Scraped {key}: {data[key]} for {url}")
            except Exception:
                data[key] = None
                logging.warning(f"Field {key} not found for {url}")

        table_rows = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '/html/body/section[2]/div/div/div[1]/div[3]/div[2]/div/div[1]/div/table/tbody/tr'))
        )
        field_mappings = {
            'Konum': 'location_temp',
            'Tapu Durumu': 'title_status',
            'Portföy Kategorisi': 'category',
            'Fiyat': 'price',
            'Metrekare (Net)': 'area_net',
            'Metre Kare (Net)': 'area_net',
            'Net Metrekare': 'area_net',
            'm² (Net)': 'area_net',
            'Metre Kare Net': 'area_net',
            'Metrekare (Brüt)': 'area_gross',
            'Metre Kare (Brüt)': 'area_gross',
            'Brüt Metrekare': 'area_gross',
            'Metre Kare Brüt': 'area_gross',
            'm² (Brüt)': 'area_gross',
            'Brüt m²': 'area_gross',
            'Brüt Alan': 'area_gross',
            'Oda Sayısı': 'room_count',
            'Bina Yaşı': 'building_age',
            'Bulunduğu Kat': 'floor',
            'Kat Sayısı': 'total_floors',
            'Isıtma': 'heating',
            'Banyo Sayısı': 'bathroom_count',
            'Balkon': 'balcony',
            'Eşyalı': 'furnished',
            'Kullanım Durumu': 'usage_status',
            'Site İçerisinde': 'in_site',
            'Krediye Uygun': 'credit_eligible',
            'Takasa uygun': 'trade_eligible',
            'İmar Durumu': 'zoning_status'
        }

        for row in table_rows:
            try:
                label = row.find_element(By.XPATH, './td[1]').text.strip()
                value = row.find_element(By.XPATH, './td[2]').text.strip()
                matched = False
                normalized_label = ''.join(label.lower().split())
                for key, field in field_mappings.items():
                    normalized_key = ''.join(key.lower().split())
                    if normalized_key in normalized_label:
                        data[field] = value
                        logging.debug(f"Scraped {field}: {value} for {url}")
                        matched = True
                        break
                if not matched:
                    logging.debug(f"No matching field for label: {label} in {url}")
            except Exception as e:
                logging.warning(f"Error processing table row for {url}: {str(e)}")
                continue

        if 'location_temp' in data and data['location_temp']:
            try:
                location_parts = [part.strip() for part in data['location_temp'].split(',')]
                if location_parts and location_parts[0].lower() == 'türkiye':
                    location_parts = location_parts[1:]
                if len(location_parts) >= 3:
                    city = location_parts[0]
                    if '-' in city:
                        city = city.split('-')[0]
                    data['city'] = city
                    data['district'] = location_parts[1]
                    data['neighborhood'] = location_parts[2]
                elif len(location_parts) == 2:
                    data['city'] = location_parts[0]
                    data['district'] = location_parts[1]
                    data['neighborhood'] = None
                elif len(location_parts) == 1:
                    data['city'] = location_parts[0]
                    data['district'] = None
                    data['neighborhood'] = None
                else:
                    data['city'] = None
                    data['district'] = None
                    data['neighborhood'] = None
                logging.debug(f"Parsed location for {url}: city={data['city']}, district={data['district']}, neighborhood={data['neighborhood']}")
            except Exception as e:
                data['city'] = None
                data['district'] = None
                data['neighborhood'] = None
                logging.warning(f"Error parsing location for {url}: {str(e)}")
        else:
            data['city'] = None
            data['district'] = None
            data['neighborhood'] = None
            logging.warning(f"Location not found for {url}")

        if 'location_temp' in data:
            del data['location_temp']

        for field in ['area_net', 'area_gross']:
            if not data.get(field):
                logging.warning(f"{field} not found for {url}")

        category = data.get('category')
        if category in ['Arsa', 'Konut İmarlı']:
            category = 'Arsa'
        elif category in ['Daire', "Villa", "Residence"]:
            category = 'Konut'
        elif category in ['Dükkan', 'Ofis', 'Depo', 'Mağaza']:
            category = 'Ticari'
        elif category in ['Otel', 'Pansiyon', 'Devremülk']:
            category = 'Turizm'
        data['category'] = category

        try:
            map_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="showMapButton"]')))
            map_button.click()
            logging.debug(f"Clicked map button for {url}")
            time.sleep(random.uniform(0.5, 1.5))

            google_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="map-canvas"]/div/div[3]/div[13]/div/a')))
            href = google_link.get_attribute('href')
            if href and 'll=' in href:
                ll_part = href.split('ll=')[1].split('&')[0]
                lat, lng = ll_part.split(',')
                try:
                    lat_val = float(lat)
                    lng_val = float(lng)
                    TURKEY_LAT_MIN, TURKEY_LAT_MAX = 35, 43
                    TURKEY_LNG_MIN, TURKEY_LNG_MAX = 25, 45
                    if (TURKEY_LAT_MIN <= lat_val <= TURKEY_LAT_MAX) and (TURKEY_LNG_MIN <= lng_val <= TURKEY_LNG_MAX):
                        data['lat'] = lat
                        data['lng'] = lng
                        logging.debug(f"Scraped lat: {lat}, lng: {lng} for {url}")
                    else:
                        data['lat'], data['lng'] = None, None
                        logging.warning(f"Coordinates out of Turkey bounds (lat: {lat}, lng: {lng}) for {url}, setting to NULL")
                except ValueError:
                    data['lat'], data['lng'] = None, None
                    logging.warning(f"Invalid lat/lng format (lat: {lat}, lng: {lng}) for {url}, setting to NULL")
            else:
                data['lat'], data['lng'] = None, None
                logging.warning(f"No valid lat/lng found in href: {href} for {url}")
        except Exception as e:
            data['lat'], data['lng'] = None, None
            logging.warning(f"Error scraping lat/lng for {url}: {str(e)}")

        listing_type = None
        listing_type_xpaths = [
            '/html/body/section[1]/div[1]/div/div[2]/div/div/div/div[1]/div[1]/span',
            '/html/body/section[1]/div[1]/div/div[2]/div/div/div/div[1]/div/span'
        ]
        for xpath in listing_type_xpaths:
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                listing_type_text = element.text.strip().lower()
                listing_type = 'Kiralık' if 'kiralık' in listing_type_text else 'Satılık'
                logging.debug(f"Scraped listing_type: {listing_type} from {xpath} for {url}")
                break
            except Exception:
                continue

        if listing_type:
            data['listing_type'] = listing_type
        else:
            data['listing_type'] = 'Satılık'
            logging.warning(f"listing_type not found for {url}, defaulting to Satılık")

        for i in range(1, 4):
            try:
                img = wait.until(EC.presence_of_element_located((By.XPATH, f'//*[@id="era-item-gallery"]/ol/li[{i}]/img')))
                data[f'image_{i}'] = img.get_attribute('src')
                logging.debug(f"Scraped image_{i}: {data[f'image_{i}']} for {url}")
            except Exception:
                data[f'image_{i}'] = None
                logging.warning(f"Image {i} not found for {url}")

        logging.info(f"Scraped details for {url}: {data}")
        return data
    except Exception as e:
        logging.error(f"Error scraping details for {url}: {str(e)}")
        return None


def save_to_db(conn, cur, data):
    if not data or not data.get('portfolio_no'):
        logging.warning(f"Skipping save for data with no portfolio_no: {data}")
        return
    try:
        columns = [
            'title', 'portfolio_no', 'agent_name', 'agent_office', 'agent_email', 'agent_phone',
            'description', 'city', 'district', 'neighborhood', 'title_status', 'category',
            'listing_type', 'price', 'area_net', 'area_gross', 'room_count', 'building_age',
            'floor', 'total_floors', 'heating', 'bathroom_count', 'balcony', 'furnished',
            'usage_status', 'in_site', 'credit_eligible', 'trade_eligible', 'zoning_status',
            'lat', 'lng', 'image_1', 'image_2', 'image_3', 'page_url'
        ]
        for col in columns:
            if col not in data:
                data[col] = None

        # Schema ve tablo adını dinamik tanımla
        table_parts = DB_TABLE.split('.')
        if len(table_parts) == 2:
            table_identifier = sql.Identifier(table_parts[0], table_parts[1])
        else:
            table_identifier = sql.Identifier(DB_TABLE)

        insert_query = sql.SQL("""
            INSERT INTO {} ({})
            VALUES ({})
            ON CONFLICT (portfolio_no) DO NOTHING
        """).format(
            table_identifier,
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


def main():
    driver, wait = None, None
    conn, cur = None, None
    try:
        driver, wait = init_driver()
        conn, cur = init_db()
        base_url = 'https://www.era.com.tr/tr-tr/Stocks/Search?mq=&stockprocesstype=&scid=&sorting=createdate%2c2&pager_p=1'
        page_urls = get_pagination_urls(driver, wait, base_url)
        for page_url in page_urls:
            listing_urls = scrape_page_listings(driver, wait, page_url)
            for url in listing_urls:
                data = scrape_listing_details(driver, wait, url)
                save_to_db(conn, cur, data)
                time.sleep(random.uniform(0.5, 1.5))
        logging.info("Scraping completed successfully.")
    except Exception as e:
        logging.error(f"Main loop error: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver closed.")
        if conn:
            cur.close()
            conn.close()
            logging.info("Database connection closed.")


if __name__ == "__main__":
    main()