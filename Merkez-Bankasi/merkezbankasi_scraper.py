import os
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Environment değişkenlerini yükle
load_dotenv()

# --- LOGGING YAPILANDIRMASI ---
logging.basicConfig(
    filename='tcmb_scraper_xml.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- ÇEVRE DEĞİŞKENLERİ ---
DB_NAME = os.getenv("DB_NAME", "your_db_name")
DB_USER = os.getenv("DB_USER", "your_db_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_db_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "your_db_port")
DB_TABLE = os.getenv("DB_TABLE", "public.merkezbank_dovizkur")

TCMB_URL = os.getenv("TCMB_URL", "https://www.tcmb.gov.tr/kurlar/today.xml")


def init_db():
    """PostgreSQL veritabanı bağlantısını başlatır."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        logging.info("Veritabanı bağlantısı başarıyla kuruldu.")
        return conn, cur
    except Exception as e:
        logging.error(f"Veritabanı bağlantı hatası: {str(e)}")
        raise


def fetch_exchange_rates():
    """TCMB XML servisinden döviz kurlarını çeker ve işler."""
    try:
        logging.info(f"Döviz kurları çekiliyor: {TCMB_URL}")

        response = requests.get(TCMB_URL, timeout=10)
        response.raise_for_status()
        logging.info("XML verisi başarıyla alındı.")

        root = ET.fromstring(response.content)

        date_str = root.get("Tarih")  # DD.MM.YYYY
        if not date_str:
            raise ValueError("XML içerisinde tarih bilgisi bulunamadı.")

        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
        date_time = date_obj.strftime('%Y-%m-%d 00:00:00')
        logging.info(f"Ayıklanan veri tarihi: {date_time}")

        currency_code_map = {
            "USD": "USD/TRY",
            "EUR": "EUR/TRY",
            "GBP": "GBP/TRY",
            "AZN": "AZN/TRY",
            "CHF": "CHF/TRY",
            "KWD": "KWD/TRY",
            "SAR": "SAR/TRY",
            "JPY": "JPY/TRY",
            "RUB": "RUB/TRY",
            "CNY": "CNY/TRY"
        }

        exchange_rates = []
        for currency in root.findall(".//Currency"):
            try:
                code = currency.get("CurrencyCode")
                if code in currency_code_map:
                    buying_elem = currency.find("ForexBuying")
                    selling_elem = currency.find("ForexSelling")
                    name_elem = currency.find("Isim")

                    buying_rate = buying_elem.text.strip() if buying_elem is not None and buying_elem.text else "0"
                    selling_rate = selling_elem.text.strip() if selling_elem is not None and selling_elem.text else "0"
                    currency_name = name_elem.text.strip() if name_elem is not None and name_elem.text else ""

                    data = {
                        "date_time": date_time,
                        "currency_code": currency_code_map[code],
                        "currency_name": currency_name,
                        "buying_rate": buying_rate,
                        "selling_rate": selling_rate
                    }

                    logging.debug(f"Veri çekildi ({data['currency_code']}): {data}")
                    exchange_rates.append(data)
            except Exception as e:
                logging.warning(f"Para birimi işlenirken hata ({code}): {str(e)}")
                continue

        logging.info(f"Toplam {len(exchange_rates)} adet döviz kuru çekildi.")
        return exchange_rates
    except Exception as e:
        logging.error(f"Döviz kurları çekilirken hata oluştu: {str(e)}")
        return []


def save_to_db(conn, cur, data):
    """Çekilen verileri veritabanına kaydeder."""
    if not data:
        logging.warning("Kaydedilecek veri bulunamadı.")
        return
    try:
        columns = ['currency_code', 'currency_name', 'buying_rate', 'selling_rate', 'date_time']

        table_parts = DB_TABLE.split('.')
        if len(table_parts) == 2:
            table_identifier = sql.Identifier(table_parts[0], table_parts[1])
        else:
            table_identifier = sql.Identifier(DB_TABLE)

        insert_query = sql.SQL("""
            INSERT INTO {} ({})
            VALUES ({})
            ON CONFLICT DO NOTHING
        """).format(
            table_identifier,
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )

        for item in data:
            cur.execute(insert_query, [item[col] for col in columns])

        conn.commit()
        logging.info(f"{len(data)} adet kayıt veritabanına eklendi.")
    except Exception as e:
        conn.rollback()
        logging.error(f"Veritabanına kayıt hatası: {str(e)}")
        raise


def main():
    conn, cur = None, None
    try:
        conn, cur = init_db()
        exchange_rates = fetch_exchange_rates()
        save_to_db(conn, cur, exchange_rates)
        logging.info("İşlem başarıyla tamamlandı.")
    except Exception as e:
        logging.error(f"Ana döngü hatası: {str(e)}")
    finally:
        if conn:
            cur.close()
            conn.close()
            logging.info("Veritabanı bağlantısı kapatıldı.")


if __name__ == "__main__":
    main()