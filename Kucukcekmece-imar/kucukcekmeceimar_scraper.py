import os
import json
import logging
from datetime import datetime
from pathlib import Path

import scrapy
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

# Dinamik Dizin Yapılandırması (Kodun çalıştığı klasörü baz alır)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
LOG_DIR = BASE_DIR / os.getenv("LOG_DIR", "logs")

# Dizinler yoksa otomatik oluştur
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Loglama Yapılandırması
LOG_FILE_PATH = LOG_DIR / os.getenv("LOG_FILE_NAME", "scraper.log")
logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class KucukcekmeceSpider(scrapy.Spider):
    name = "kucukcekmece"

    # Dosya Yolları (Dinamik ve Esnek)
    output_file = DATA_DIR / os.getenv("OUTPUT_EXCEL_NAME", "output.xlsx")
    input_file = DATA_DIR / os.getenv("INPUT_TXT_NAME", "cikti.txt")
    processed_ids_file = DATA_DIR / os.getenv("PROCESSED_IDS_NAME", "processed_ids.txt")
    output_text_file = DATA_DIR / os.getenv("OUTPUT_TEXT_NAME", "output_data.txt")

    def start_requests(self):
        # İşlenmiş parsel_id'leri oku
        processed_ids = set()
        if self.processed_ids_file.exists():
            with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                processed_ids = set(line.strip() for line in f if line.strip())
            logging.info(f"{len(processed_ids)} işlenmiş parsel_id bulundu.")
        else:
            logging.info("processed_ids.txt dosyası bulunamadı, yeni dosya oluşturulacak.")

        # Girdi dosyasından parsel_id'leri oku ve işlenmiş olanları hariç tut
        if not self.input_file.exists():
            logging.error(f"Girdi dosyası bulunamadı: {self.input_file}")
            return

        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                parsel_ids = [line.strip() for line in f if line.strip() and line.strip() not in processed_ids]
            logging.info(f"{len(parsel_ids)} yeni parsel_id okundu.")
        except Exception as e:
            logging.error(f"Girdi dosyası okuma hatası: {e}")
            return

        for parsel_id in parsel_ids:
            url = f"https://keos.kucukcekmece.bel.tr/imardurumu/imar.aspx?parselid={parsel_id}"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'parsel_id': parsel_id},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive'
                },
                dont_filter=True
            )

    def parse(self, response):
        parsel_id = response.meta['parsel_id']
        logging.info(f"Processing parsel_id: {parsel_id}")

        json_data, page_url_1_list, object_id_list = self.parse_html_to_json(response.text, parsel_id)

        if json_data:
            logging.info(f"parsel_id {parsel_id}: JSON data extracted successfully.")
            for url in page_url_1_list:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_page_url_1,
                    meta={
                        'parsel_id': parsel_id,
                        'json_data': json_data,
                        'page_url_1_list': page_url_1_list,
                        'object_id_list': object_id_list,
                        'page_url': response.url
                    },
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    },
                    dont_filter=True
                )
        else:
            logging.warning(f"parsel_id {parsel_id}: No JSON data extracted.")

    def parse_page_url_1(self, response):
        parsel_id = response.meta['parsel_id']
        json_data = response.meta['json_data']
        page_url_1_list = response.meta['page_url_1_list']
        object_id_list = response.meta['object_id_list']
        page_url = response.meta['page_url']

        logging.info(f"parsel_id {parsel_id}: Fetching page_url_1_detay from {response.url}")

        try:
            response_text = response.body.decode('iso-8859-9')
            page_url_1_detay = json.loads(response_text)
            logging.info(f"parsel_id {parsel_id}: page_url_1_detay fetched successfully.")
        except Exception as e:
            logging.error(f"parsel_id {parsel_id}: Error fetching page_url_1_detay: {e}")
            error_file = LOG_DIR / f'error_page_url_1_{parsel_id}.txt'
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            page_url_1_detay = None

        item = {
            'parsel_id': parsel_id,
            'data_json': json.dumps(json_data, ensure_ascii=False),
            'page_url_1': json.dumps(page_url_1_list, ensure_ascii=False),
            'object_id': json.dumps(object_id_list, ensure_ascii=False),
            'page_url': page_url,
            'auto_rec_time': str(datetime.now()),
            'page_url_1_detay': json.dumps(page_url_1_detay, ensure_ascii=False) if page_url_1_detay else ''
        }

        self.save_to_excel(item)
        logging.info(f"parsel_id {item['parsel_id']} successfully processed.")

    def parse_html_to_json(self, html_content, parsel_id):
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            html_output = soup.find("div", {"id": "htmlOutput", "class": "col"})
            if not html_output:
                logging.error(f"parsel_id {parsel_id}: <div id='htmlOutput'> not found.")
                error_html = LOG_DIR / f'error_html_{parsel_id}.html'
                with open(error_html, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                return None, None, None

            json_data = {}
            page_url_1_list = []
            object_id_list = []
            rows = html_output.find_all("div", class_="divTableRow")
            for row in rows:
                label = row.find("div", class_="divTableCellLabel")
                content = row.find("div", class_="divTableContent")

                if label and content:
                    label_text = label.get_text(strip=True)
                    content_text = content.get_text(strip=True)

                    if "KADASTRO PARSEL KONUM BİLGİSİ" in label_text and "EMPTYROW" in content_text:
                        continue

                    links = content.find_all('a')
                    if links:
                        if label_text == "Fonksiyon":
                            link_data = {'value': content_text, 'link': []}
                            for link in links:
                                link_info = {
                                    'url': link.get('href', ''),
                                    'title': link.get('title', ''),
                                    'platform': link.get_text(strip=True)
                                }
                                if 'data-service' in link.attrs and link.get('data-service') == 'planfonksiyonview' and link.get('data-ref'):
                                    link_info['data-service'] = link.get('data-service')
                                    link_info['data-ref'] = link.get('data-ref')
                                    details, fetched_url, fetched_objectid = self.fetch_fonksiyon_details(link.get('data-ref'), parsel_id)
                                    if details:
                                        link_info['details'] = details
                                    if fetched_url and fetched_url not in page_url_1_list:
                                        page_url_1_list.append(fetched_url)
                                    if fetched_objectid and fetched_objectid not in object_id_list:
                                        object_id_list.append(fetched_objectid)
                                link_data['link'].append(link_info)
                            json_data[label_text] = link_data
                        elif len(links) == 1:
                            link = links[0]
                            link_data = {
                                'value': content_text,
                                'link': {
                                    'url': link.get('href', ''),
                                    'title': link.get('title', ''),
                                    'data-service': link.get('data-service', ''),
                                    'data-ref': link.get('data-ref', '')
                                }
                            }
                            if link_data['link']['data-service'] == 'planfonksiyonview' and link_data['link']['data-ref']:
                                details, fetched_url, fetched_objectid = self.fetch_fonksiyon_details(link_data['link']['data-ref'], parsel_id)
                                if details:
                                    link_data['link']['details'] = details
                                if fetched_url and fetched_url not in page_url_1_list:
                                    page_url_1_list.append(fetched_url)
                                if fetched_objectid and fetched_objectid not in object_id_list:
                                    object_id_list.append(fetched_objectid)
                            json_data[label_text] = link_data
                        else:
                            link_data = {
                                'value': content_text,
                                'link': [
                                    {
                                        'url': link.get('href', ''),
                                        'title': link.get('title', ''),
                                        'platform': link.get_text(strip=True)
                                    } for link in links
                                ]
                            }
                            json_data[label_text] = link_data
                    else:
                        if label_text == "Tadilat Adı":
                            json_data[label_text] = {
                                'value': [item.strip() for item in content_text.split(',') if item.strip()]
                            }
                        else:
                            json_data[label_text] = {'value': content_text}

            if any("Koordinat" in key or "Projeksiyon" in key or "MEGSİS" in key for key in json_data):
                kadastro = {}
                for key in list(json_data.keys()):
                    if "Projeksiyon" in key or "Kartezyen Koordinat" in key or "Coğrafi Koordinat" in key or "MEGSİS" in key:
                        kadastro[key] = json_data.pop(key)
                json_data["Kadastro Parsel Konum Bilgisi"] = kadastro

            return json_data if json_data else None, page_url_1_list, object_id_list
        except Exception as e:
            logging.error(f"parsel_id {parsel_id}: Error in parse_html_to_json: {e}")
            return None, None, None

    def fetch_fonksiyon_details(self, data_ref, parsel_id):
        try:
            objectid, ref_parsel_id = data_ref.split(',')
            url = f"https://keos.kucukcekmece.bel.tr/imardurumu/service/imarsvc.aspx?type=planfonksiyonview&objectid={objectid}&parsel_id={ref_parsel_id}"
            return None, url, objectid
        except Exception as e:
            logging.error(f"parsel_id {parsel_id}: Error in fetch_fonksiyon_details: {e}")
            return None, None, None

    def save_to_text(self, item):
        try:
            with open(self.output_text_file, 'a', encoding='utf-8') as f:
                json.dump(item, f, ensure_ascii=False)
                f.write('\n')
            with open(self.processed_ids_file, 'a', encoding='utf-8') as f:
                f.write(f"{item['parsel_id']}\n")
            logging.info(f"parsel_id {item['parsel_id']} metin dosyasına kaydedildi.")
        except Exception as e:
            logging.error(f"Metin dosyasına kaydetme hatası: {e}")

    def save_to_excel(self, item):
        self.save_to_text(item)
        df = pd.DataFrame([item])
        try:
            if self.output_file.exists():
                existing_df = pd.read_excel(self.output_file)
                df = pd.concat([existing_df, df], ignore_index=True)
            df.to_excel(self.output_file, index=False)
            logging.info(f"parsel_id {item['parsel_id']} Excel'e kaydedildi.")
        except Exception as e:
            logging.error(f"Excel kaydetme hatası: {e}")


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess

    process = CrawlerProcess(settings={
        "CONCURRENT_REQUESTS": 5,
        "DOWNLOAD_DELAY": 3,
        "LOG_LEVEL": "INFO",
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "HANDLE_HTTPSTATUS_LIST": [301, 302, 303, 307, 308],
        "REDIRECT_ENABLED": True,
        "REDIRECT_MAX_TIMES": 5,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_TIMEOUT": 10
    })

    process.crawl(KucukcekmeceSpider)
    process.start()