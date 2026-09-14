import os
import time
import random
import logging
from datetime import datetime
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
        wait = WebDriverWait(driver, 15)
        logging.info("WebDriver initialized successfully")
        return driver, wait
    except Exception as e:
        logging.error(f"Error initializing WebDriver: {str(e)}")
        raise

# PostgreSQL veritabanı bağlantısı
def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logging.info("Database connection established")
        return conn, cur
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        raise

# Döviz kurlarını çekme fonksiyonu
def scrape_exchange_rates(driver, wait):
    try:
        url = "https://www.altinkaynak.com/Doviz/Kur/Guncel"
        driver.get(url)
        time.sleep(random.uniform(2, 3))
        logging.info(f"Accessed Altinkaynak page: {url}")

        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="trUSD"]')))
        logging.info("Table loaded successfully")

        currencies = [
            {"code": "USD/TRY", "name_xpath": '//*[@id="trUSD"]/td[1]/h5', "buy_xpath": '//*[@id="tdUSDBuy"]', "sell_xpath": '//*[@id="tdUSDSell"]'},
            {"code": "EUR/TRY", "name_xpath": '//*[@id="trEUR"]/td[1]/h5', "buy_xpath": '//*[@id="tdEURBuy"]', "sell_xpath": '//*[@id="tdEURSell"]'},
            {"code": "GBP/TRY", "name_xpath": '//*[@id="trGBP"]/td[1]/h5', "buy_xpath": '//*[@id="tdGBPBuy"]', "sell_xpath": '//*[@id="tdGBPSell"]'},
            {"code": "AZN/TRY", "name_xpath": '//*[@id="trAZN"]/td[1]/h5', "buy_xpath": '//*[@id="tdAZNBuy"]', "sell_xpath": '//*[@id="tdAZNSell"]'},
            {"code": "CHF/TRY", "name_xpath": '//*[@id="trCHF"]/td[1]/h5', "buy_xpath": '//*[@id="tdCHFBuy"]', "sell_xpath": '//*[@id="tdCHFSell"]'},
            {"code": "KWD/TRY", "name_xpath": '//*[@id="trKWD"]/td[1]/h5', "buy_xpath": '//*[@id="tdKWDBuy"]', "sell_xpath": '//*[@id="tdKWDSell"]'},
            {"code": "SAR/TRY", "name_xpath": '//*[@id="trSAR"]/td[1]/h5', "buy_xpath": '//*[@id="tdSARBuy"]', "sell_xpath": '//*[@id="tdSARSell"]'},
            {"code": "JPY/TRY", "name_xpath": '//*[@id="trJPY"]/td[1]/h5', "buy_xpath": '//*[@id="tdJPYBuy"]', "sell_xpath": '//*[@id="tdJPYSell"]'},
            {"code": "RUB/TRY", "name_xpath": '//*[@id="trRUB"]/td[1]/h5', "buy_xpath": '//*[@id="tdRUBBuy"]', "sell_xpath": '//*[@id="tdRUBSell"]'},
            {"code": "CNY/TRY", "name_xpath": '//*[@id="trCNY"]/td[1]/h5', "buy_xpath": '//*[@id="tdCNYBuy"]', "sell_xpath": '//*[@id="tdCNYSell"]'},
        ]

        exchange_rates = []
        date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for currency in currencies:
            try:
                name_elements = driver.find_elements(By.XPATH, currency["name_xpath"])
                currency_name = name_elements[0].text.strip() if name_elements else "N/A"

                buy_element = driver.find_element(By.XPATH, currency["buy_xpath"])
                buying_rate = buy_element.text.strip()

                sell_element = driver.find_element(By.XPATH, currency["sell_xpath"])
                selling_rate = sell_element.text.strip()

                data = {
                    "currency_code": currency["code"],
                    "currency_name": currency_name,
                    "buying_rate": buying_rate,
                    "selling_rate": selling_rate,
                    "date_time": date_time
                }

                exchange_rates.append(data)
            except Exception as e:
                logging.warning(f"Error processing currency {currency['code']}: {str(e)}")
                continue

        logging.info(f"Scraped {len(exchange_rates)} exchange rates")
        return exchange_rates
    except Exception as e:
        logging.error(f"Error scraping exchange rates: {str(e)}")
        return []

# Veritabanına kaydetme
def save_to_db(conn, cur, data):
    if not data:
        logging.warning("No data to save")
        return
    try:
        columns = ['currency_code', 'currency_name', 'buying_rate', 'selling_rate', 'date_time']
        
        # Genel tablo ismi kullanıldı: public.currency_rates
        insert_query = sql.SQL("""
            INSERT INTO public.currency_rates ({})
            VALUES ({})
            ON CONFLICT (currency_code)
            DO UPDATE SET
                currency_name = EXCLUDED.currency_name,
                buying_rate = EXCLUDED.buying_rate,
                selling_rate = EXCLUDED.selling_rate,
                date_time = EXCLUDED.date_time
        """).format(
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )
        for item in data:
            cur.execute(insert_query, [item[col] for col in columns])
        conn.commit()
        logging.info(f"Saved/Updated {len(data)} records to database")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error saving data to database: {str(e)}")
        raise

# Ana fonksiyon
def main():
    driver, wait = None, None
    conn, cur = None, None
    try:
        driver, wait = init_driver()
        conn, cur = init_db()
        exchange_rates = scrape_exchange_rates(driver, wait)
        save_to_db(conn, cur, exchange_rates)
        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Main loop error: {str(e)}")
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