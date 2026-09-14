# Python Projelerim

Bu repo, gayrimenkul platformları, kamu/belediye imar portalları ve 
finansal kaynaklardan veri kazıma (web scraping), veri temizleme ve otomasyon 
süreçlerine yönelik geliştirdiğim Python projelerini barındırmaktadır.

## 📁 Proje Yapısı

```
.
├── Altin-Emlak/
│   └── ...
├── Altinkaynak/
│   └── ...
├── Century21/
│   └── ...
├── Coldwell-Banker/
│   └── ...
├── Era/
│   └── ...
├── Guncel-Projeler/      
│   └── ...
├── Hepsi-Emlak/
│   └── ...
├── Kucukcekmece-imar/
│   └── ...
├── Merkez-Bankasi/
│   └── ...
├── Milli-Emlak/
│   └── ...
├── Realty-World/
│   └── ...
├── Remax/
│   └── ...
├── requirements
├── .gitignore
└── README.md
```


## 📌 Proje Özeti

| Klasör / Proje | Açıklama | Teknolojiler |
|---|---|---|
| `Altin-Emlak` | Altın Emlak portföy verilerini ve bölgesel ilan detaylarını otomatize şekilde toplar. | Scrapy, Pandas |
| `Altinkaynak` | Canlı döviz, altın ve ziynet fiyat verilerini anlık olarak çeken finansal scraping script'i. | Requests, BeautifulSoup4 |
| `Century21` | Century 21 platformundaki güncel gayrimenkul ilan verilerini parse eder ve işler. | Requests, BeautifulSoup4 |
| `Coldwell-Banker` | Coldwell Banker portföyündeki konut ve ticari gayrimenkul verilerini kazır. | Scrapy, Lxml |
| `Era` | ERA Real Estate ilan detaylarını ve harita/konum verilerini çeken otomasyon betiği. | Requests, Pandas |
| `Guncel-Projeler` | Çeşitli gayrimenkul projelerine ait lansman, fiyat ve lokasyon verilerini derleyen otomasyon. | Scrapy, Pandas |
| `Hepsi-Emlak` | İlan platformundaki gayrimenkul verilerini, fiyat/konum parametrelerini çekerek veri analizine uygun formata getirir. | Requests, BeautifulSoup4, Pandas |
| `Kucukcekmece-imar` | Küçükçekmece Belediyesi KEOS imar verilerini ve parsel fonksiyon detaylarını asenkron olarak kazır, JSON ve Excel formatında dinamik loglama ile kaydeder. | Scrapy, BeautifulSoup4, Pandas, Python-dotenv |
| `Merkez-Bankasi` | TCMB döviz kurları, faiz oranları ve finansal gösterge verilerini çekip yapılandırır. | Requests, Pandas, XML parsing |
| `Milli-Emlak` | Milli Emlak duyurularını, taşınmaz satış ve kiralama ihale listelerini takip edip kaydeder. | Scrapy, BeautifulSoup4 |
| `Realty-World` | Realty World platformundaki ilan verilerini otomatize şekilde çeken kazıma modülü. | BeautifulSoup4, Requests |
| `Remax` | Remax portföyündeki ilan detaylarını, gayrimenkul tiplerini ve fiyat geçmişlerini toplar. | Scrapy, Pandas |


## 🛠️ Kullanılan Teknolojiler

- **Dili:** Python 3.10+
- **Web Scraping & HTML Parsing:** Scrapy, BeautifulSoup4, Lxml, Requests
- **Veri İşleme & Yapılandırma:** Pandas, OpenPyXL, JSON Parsing
- **Güvenlik & Yapılandırma:** Python-dotenv (`.env` entegrasyonu)


## 🚀 Çalıştırma

Her klasördeki scriptler bağımsız çalışacak şekilde tasarlanmıştır. İlgili
klasöre girip script'i çalıştırmanız yeterlidir:

```bash
cd Altin-Emlak
python altinemlak_scraper.py
```

Eğer bazı projeler ek kütüphane gerektiriyorsa, projenin kök dizinine bir
`requirements.txt` eklenmesi önerilir:

```bash
pip install -r requirements.txt
```



## 📄 Lisans

Bu proje kişisel öğrenme, veri mühendisliği pratikleri ve portföy sergileme amacıyla geliştirilmiştir. 
Kodlar açık kaynaklıdır; inceleyebilir veya eğitim amaçlı kullanabilirsiniz. 
Ticari kullanım veya özel iş birliği talepleri için benimle LinkedIn üzerinden iletişime geçebilirsiniz.