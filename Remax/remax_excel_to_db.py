import os
from pathlib import Path
import logging
import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Logging Yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Çalışma dizini ve varsayılan dosya yolları
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data" / "excel"))
EXCEL_FILE_NAME = os.getenv("EXCEL_FILE_NAME", "konut_ilan_detaylari.xlsx")
EXCEL_PATH = DATA_DIR / EXCEL_FILE_NAME

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
TABLE_NAME = os.getenv("DB_TABLE", "scrap_ad_remax")

# Excel kolonları ile DB kolonlarının eşleştirme haritası
EXCEL_TO_DB_MAP = {
    'Link': 'ad_page_url',
    'Başlık': 'ad_page_title',
    'İlan No': 'ad_no',
    'Açıklama': 'ad_comment',
    'İl': 'ad_province',
    'İlçe': 'ad_district',
    'Mahalle': 'ad_neighborhood',
    'İlan Durumu': 'ad_status',
    'Kategori': 'ad_category',
    'Alt Kategori': 'ad_subcategory',
    'Brüt Metrekare': 'ad_square_gross_area',
    'Net Metrekare': 'ad_square_net_area',
    'Fiyat': 'ad_pure_price',
    'Oda Sayısı': 'ad_build_room',
    'Bina Yaşı': 'ad_build_age',
    'Toplam Kat Sayısı': 'ad_build_floor',
    'Bulunduğu Kat': 'ad_build_current_floor',
    'Kullanım Durumu': 'ad_using_status',
    'Yapı Durumu': 'ad_structure_status',
    'Eşyalı': 'ad_goods_status',
    'İlanı Veren': 'ad_from',
    'Krediye Uygun': 'ad_creditable',
    'GSM No': 'contact_gsm',
    'Sabit Telefon': 'contact_phone',
    'İletişim Adı': 'contact_name',
    'Mail': 'authority',
    'Resim 1 URL': 'ad_picture',
    'Resim 2 URL': 'ad_picture_2',
    'Resim 3 URL': 'ad_picture_3',
    'Resim 4 URL': 'ad_picture_4',
    'Resim 5 URL': 'ad_picture_5',
    'Lat': 'lat',
    'Lng': 'lng'
}


def load_and_prepare_data(file_path):
    """Excel dosyasını okur, sütunları eşleştirir ve veri çerçevesini temizler."""
    if not file_path.exists():
        logging.error(f"Excel dosyası bulunamadı: {file_path}")
        return None

    try:
        df = pd.read_excel(file_path)
        common_columns = [col for col in EXCEL_TO_DB_MAP if col in df.columns]

        if not common_columns:
            logging.warning("Excel dosyasında eşleşen sütun bulunamadı!")
            return None

        # Sadece eşleşen sütunları filtrele ve yeniden adlandır
        df = df[common_columns].rename(columns=EXCEL_TO_DB_MAP)
        
        # NaN / NULL değerlerini Python None tipine çevir (PostgreSQL uyumluluğu için)
        df = df.where(pd.notnull(df), None)
        return df
    except Exception as e:
        logging.error(f"Excel dosyası işlenirken hata oluştu: {e}")
        return None


def insert_to_database(df):
    """Hazırlanan veriyi PostgreSQL veritabanına güvenli ve toplu olarak ekler."""
    conn, cur = None, None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Dinamik şema ve tablo identifier oluşturma (SQL Injection önlemi)
        table_identifier = sql.Identifier(SCHEMA_NAME, TABLE_NAME)
        columns = list(df.columns)
        
        # Güvenli SQL Sorgusu Hazırlama
        insert_query = sql.SQL("""
            INSERT INTO {} ({})
            VALUES ({})
        """).format(
            table_identifier,
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )

        # Veriyi tuple listesine dönüştür
        records = [tuple(row) for row in df.itertuples(index=False, name=None)]

        # Toplu veri ekleme (Batch Insert)
        execute_batch(cur, insert_query, records, page_size=100)
        conn.commit()
        logging.info(f"{len(records)} adet veri başarıyla veritabanına aktarıldı.")

    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Veritabanına kaydederken hata oluştu: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
            logging.info("Veritabanı bağlantısı kapatıldı.")


def main():
    logging.info("Aktarım işlemi başlatılıyor...")
    df = load_and_prepare_data(EXCEL_PATH)
    if df is not None and not df.empty:
        insert_to_database(df)
    else:
        logging.warning("Aktarılacak geçerli veri bulunamadı.")


if __name__ == "__main__":
    main()