"""
Google Groups Scraper - Hava Savunma Sistemleri Yarışması
=========================================================
Bu script Google Groups'taki soru-cevapları kazır ve önemli olanları filtreler.

Kullanım:
    python google_groups_scraper.py

Çalışma mantığı:
    1. Chrome açılır, Google hesabınla giriş yapman için 60 saniye bekler
    2. Tüm konu başlıklarını toplar (scroll ile)
    3. Her konunun içine girer, mesajları çeker
    4. Tüm veriyi JSON + CSV olarak kaydeder
    5. Önemli mesajları anahtar kelimeye göre filtreler
"""

import json
import csv
import time
import os
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# AYARLAR
# ============================================================

GROUP_URL = "https://groups.google.com/g/2024-hava-savunma-sstemler-yarimasi"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrape_output")
LOGIN_WAIT_SECONDS = 90  # Giriş yapmak için bekleme süresi

# Önemli mesajları filtrelemek için anahtar kelimeler
IMPORTANT_KEYWORDS = [
    # Yarışma kuralları ve organizasyon
    "kural", "değişiklik", "güncelleme", "duyuru", "ilan",
    "deadline", "son tarih", "teslim", "süre",
    "puan", "puanlama", "değerlendirme", "skor", "sıralama",
    "final", "yarı final", "eleme",
    
    # Teknik terimler - Hava Savunma
    "radar", "füze", "mühimmat", "atış", "hedef",
    "algılama", "takip", "tracking", "detection",
    "simülasyon", "senaryo", "tehdit",
    "menzil", "irtifa", "hız", "açı",
    "angajman", "interceptor", "engagement",
    
    # Yazılım / Teknik
    "api", "sdk", "protokol", "format", "dosya",
    "koordinat", "veri", "data", "parametre",
    "hata", "bug", "düzeltme", "fix", "patch",
    "sürüm", "versiyon", "version", "update",
    "kod", "algoritma", "fonksiyon",
    
    # Önemli sorular
    "nasıl", "neden", "zorunlu", "gerekli", "şart",
    "yasak", "izin", "sınır", "limit", "kısıt",
    "örnek", "sample", "template", "şablon",
    
    # Organizatör cevapları ipuçları
    "açıklama", "cevap", "yanıt", "bilgilendirme",
    "dikkat", "önemli", "uyarı", "hatırlatma",
]


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def setup_driver():
    """Chrome WebDriver'ı yapılandır ve başlat."""
    chrome_options = Options()
    # Tarayıcı kapanmasını engelle (debug için)
    chrome_options.add_experimental_option("detach", True)
    # Bot algılamayı azalt
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # Dil ayarı
    chrome_options.add_argument("--lang=tr")
    chrome_options.add_argument("--start-maximized")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Navigator.webdriver flag'ini gizle
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def wait_for_login(driver):
    """Kullanıcının Google hesabına giriş yapmasını bekle."""
    driver.get("https://accounts.google.com")
    print("\n" + "=" * 60)
    print("🔐 GOOGLE HESABINIZA GİRİŞ YAPIN")
    print("=" * 60)
    print(f"Tarayıcıda Google hesabınıza giriş yapın.")
    print(f"Giriş yaptıktan sonra {LOGIN_WAIT_SECONDS} saniye içinde otomatik devam edecek.")
    print("Veya giriş yaptıktan sonra terminalde ENTER'a basın...")
    print("=" * 60 + "\n")
    
    # Kullanıcı giriş yapana kadar bekle
    for i in range(LOGIN_WAIT_SECONDS, 0, -1):
        try:
            # Giriş yapılmış mı kontrol et
            driver.get("https://myaccount.google.com")
            time.sleep(2)
            page_source = driver.page_source
            if "Oturum açın" not in page_source and "Sign in" not in page_source:
                print("✅ Giriş başarılı!")
                return True
        except Exception:
            pass
        
        if i % 10 == 0:
            print(f"⏳ Kalan süre: {i} saniye...")
        time.sleep(1)
    
    return False


def scroll_to_load_all_topics(driver):
    """Sayfayı aşağı kaydırarak tüm konuları yükle."""
    print("\n📜 Tüm konular yükleniyor (scroll)...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_count = 0
    
    while no_change_count < 5:  # 5 kez aynı yükseklik = tüm içerik yüklenmiş
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
        else:
            no_change_count = 0
        last_height = new_height
    
    print("✅ Tüm konular yüklendi.")


def get_all_topic_links(driver):
    """Sayfadaki tüm konu başlıklarının linklerini topla."""
    print("\n🔗 Konu linkleri toplanıyor...")
    
    topic_links = []
    
    # Google Groups'ta konular genelde <a> etiketlerinde
    # Birkaç farklı CSS selector deneyelim
    selectors = [
        "a[href*='/c/']",           # /g/GROUP_NAME/c/TOPIC_ID formatı
        "a[href*='/d/msgid/']",     # Mesaj ID formatı
        ".VhJfce a",                # Konu listesi class'ı
        "[role='listitem'] a",      # Liste elemanları
        "a.WtV5nd",                 # Konu başlık class'ı
        "a[data-topic-id]",         # Data attribute ile
    ]
    
    found_links = set()
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                href = elem.get_attribute("href")
                if href and "/c/" in href:
                    found_links.add(href)
        except Exception:
            continue
    
    # Eğer CSS selector çalışmadıysa, tüm linkleri tara
    if not found_links:
        print("⚠️  Standart selector'lar çalışmadı, tüm linkler taranıyor...")
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                href = link.get_attribute("href")
                if href and "2024-hava-savunma" in href and ("/c/" in href or "/d/" in href):
                    found_links.add(href)
            except StaleElementReferenceException:
                continue
    
    topic_links = list(found_links)
    print(f"✅ {len(topic_links)} konu linki bulundu.")
    
    return topic_links


def scrape_topic(driver, topic_url, index, total):
    """Bir konunun içeriğini kazı."""
    print(f"\n📖 [{index}/{total}] Konu kazınıyor: {topic_url[:80]}...")
    
    topic_data = {
        "url": topic_url,
        "title": "",
        "messages": [],
        "scraped_at": datetime.now().isoformat()
    }
    
    try:
        driver.get(topic_url)
        time.sleep(3)  # Sayfanın yüklenmesini bekle
        
        # Başlığı çek
        try:
            # Farklı selector'lar dene
            title_selectors = [
                "h2", "h1",
                ".bVEBo", ".Wpcqbe",  # Google Groups title class'ları
                "[role='heading']",
                ".TWaSJe"
            ]
            for sel in title_selectors:
                try:
                    title_elem = driver.find_element(By.CSS_SELECTOR, sel)
                    if title_elem.text.strip():
                        topic_data["title"] = title_elem.text.strip()
                        break
                except NoSuchElementException:
                    continue
        except Exception:
            topic_data["title"] = "Başlık bulunamadı"
        
        # "Tüm mesajları göster" butonu varsa tıkla
        try:
            expand_buttons = driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'daha fazla') or contains(text(), 'more') or contains(text(), 'tümü')]")
            for btn in expand_buttons:
                try:
                    btn.click()
                    time.sleep(1)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Mesajları çek
        # Google Groups mesaj container'ları
        message_selectors = [
            ".kMZJse",          # Mesaj container
            ".gs",              # Eski format
            "[data-message-id]",# Mesaj ID attribute
            ".WtV5nd",          # Mesaj class
            ".cjEMHb",          # Alternatif mesaj class
        ]
        
        messages_found = False
        
        for selector in message_selectors:
            try:
                msg_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if msg_elements:
                    for msg_elem in msg_elements:
                        msg_data = extract_message_data(driver, msg_elem)
                        if msg_data:
                            topic_data["messages"].append(msg_data)
                    messages_found = True
                    break
            except Exception:
                continue
        
        # Eğer selector'lar çalışmadıysa, sayfanın tüm text'ini al
        if not messages_found:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                topic_data["messages"].append({
                    "author": "Bilinmeyen",
                    "date": "",
                    "content": body_text,
                    "is_raw": True
                })
            except Exception:
                pass
        
        print(f"   ✅ Başlık: {topic_data['title'][:50]}... | {len(topic_data['messages'])} mesaj")
        
    except Exception as e:
        print(f"   ❌ Hata: {str(e)[:100]}")
        topic_data["error"] = str(e)
    
    return topic_data


def extract_message_data(driver, msg_element):
    """Bir mesaj elementinden veri çek."""
    msg_data = {
        "author": "",
        "date": "",
        "content": "",
    }
    
    try:
        # Yazar
        author_selectors = [".BbVMab", ".aBRFpe", "[data-name]", "span[dir='auto']"]
        for sel in author_selectors:
            try:
                author_elem = msg_element.find_element(By.CSS_SELECTOR, sel)
                if author_elem.text.strip():
                    msg_data["author"] = author_elem.text.strip()
                    break
            except NoSuchElementException:
                continue
        
        # Tarih
        date_selectors = [".GJRJHe", ".gHwGle", "time", "[datetime]", "span[title]"]
        for sel in date_selectors:
            try:
                date_elem = msg_element.find_element(By.CSS_SELECTOR, sel)
                date_text = date_elem.get_attribute("datetime") or date_elem.get_attribute("title") or date_elem.text
                if date_text:
                    msg_data["date"] = date_text.strip()
                    break
            except NoSuchElementException:
                continue
        
        # İçerik
        content_selectors = [".jHPlBe", ".maQs7", ".gmail_default", "div[dir='ltr']", "div[dir='auto']"]
        for sel in content_selectors:
            try:
                content_elem = msg_element.find_element(By.CSS_SELECTOR, sel)
                if content_elem.text.strip():
                    msg_data["content"] = content_elem.text.strip()
                    break
            except NoSuchElementException:
                continue
        
        # İçerik hala boşsa, tüm text'i al
        if not msg_data["content"]:
            msg_data["content"] = msg_element.text.strip()
        
        return msg_data if msg_data["content"] else None
        
    except Exception:
        return None


def filter_important(all_topics, keywords=IMPORTANT_KEYWORDS):
    """Anahtar kelimelere göre önemli mesajları filtrele."""
    print("\n🔍 Önemli mesajlar filtreleniyor...")
    
    important_topics = []
    
    for topic in all_topics:
        topic_text = topic["title"].lower()
        important_messages = []
        keyword_matches = set()
        
        for msg in topic.get("messages", []):
            content = msg.get("content", "").lower()
            full_text = topic_text + " " + content
            
            matched = []
            for kw in keywords:
                if kw.lower() in full_text:
                    matched.append(kw)
                    keyword_matches.add(kw)
            
            if matched:
                msg_copy = msg.copy()
                msg_copy["matched_keywords"] = matched
                important_messages.append(msg_copy)
        
        if important_messages:
            important_topics.append({
                "title": topic["title"],
                "url": topic["url"],
                "keyword_matches": list(keyword_matches),
                "match_count": len(keyword_matches),
                "messages": important_messages,
            })
    
    # Eşleşme sayısına göre sırala (en çok eşleşen en üstte)
    important_topics.sort(key=lambda x: x["match_count"], reverse=True)
    
    print(f"✅ {len(important_topics)} önemli konu bulundu (toplam {len(all_topics)} konu içinden).")
    
    return important_topics


def save_results(all_topics, important_topics, output_dir):
    """Sonuçları dosyalara kaydet."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Tüm veriler - JSON
    all_path = os.path.join(output_dir, "tum_konular.json")
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(all_topics, f, ensure_ascii=False, indent=2)
    print(f"📁 Tüm konular: {all_path}")
    
    # 2. Filtrelenmiş önemli veriler - JSON
    imp_path = os.path.join(output_dir, "onemli_konular.json")
    with open(imp_path, "w", encoding="utf-8") as f:
        json.dump(important_topics, f, ensure_ascii=False, indent=2)
    print(f"📁 Önemli konular: {imp_path}")
    
    # 3. CSV - kolay görüntüleme için
    csv_path = os.path.join(output_dir, "onemli_konular.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Konu Başlığı", "URL", "Eşleşen Anahtar Kelimeler", "Eşleşme Sayısı", "Yazar", "Tarih", "Mesaj İçeriği"])
        
        for topic in important_topics:
            for msg in topic["messages"]:
                writer.writerow([
                    topic["title"],
                    topic["url"],
                    ", ".join(topic["keyword_matches"]),
                    topic["match_count"],
                    msg.get("author", ""),
                    msg.get("date", ""),
                    msg.get("content", "")[:500],  # İlk 500 karakter
                ])
    print(f"📁 CSV dosyası: {csv_path}")
    
    # 4. Özet rapor - Markdown
    report_path = os.path.join(output_dir, "rapor.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🛡️ Hava Savunma Sistemleri Yarışması - Google Groups Raporu\n\n")
        f.write(f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"📊 Toplam konu sayısı: **{len(all_topics)}**\n\n")
        f.write(f"⭐ Önemli konu sayısı: **{len(important_topics)}**\n\n")
        f.write("---\n\n")
        
        for i, topic in enumerate(important_topics, 1):
            f.write(f"## {i}. {topic['title']}\n\n")
            f.write(f"🔗 [Link]({topic['url']})\n\n")
            f.write(f"🏷️ Anahtar kelimeler: `{'`, `'.join(topic['keyword_matches'])}`\n\n")
            
            for msg in topic["messages"]:
                author = msg.get("author", "Bilinmeyen")
                date = msg.get("date", "")
                content = msg.get("content", "")
                f.write(f"**{author}** ({date}):\n\n")
                f.write(f"> {content[:1000]}\n\n")
            
            f.write("---\n\n")
    
    print(f"📁 Rapor: {report_path}")


# ============================================================
# ANA FONKSİYON
# ============================================================

def main():
    print("=" * 60)
    print("🛡️  Google Groups Scraper")
    print("    Hava Savunma Sistemleri Yarışması")
    print("=" * 60)
    
    # 1. WebDriver başlat
    print("\n🚀 Chrome başlatılıyor...")
    driver = setup_driver()
    
    try:
        # 2. Giriş yap
        logged_in = wait_for_login(driver)
        if not logged_in:
            print("❌ Giriş yapılamadı! Yine de devam ediliyor...")
        
        # 3. Grup sayfasına git
        print(f"\n🌐 Gruba gidiliyor: {GROUP_URL}")
        driver.get(GROUP_URL)
        time.sleep(5)
        
        # Erişim kontrolü
        page_source = driver.page_source
        if "don't have permission" in page_source or "izniniz yok" in page_source.lower():
            print("❌ Gruba erişim izniniz yok! Giriş yapıp gruba üye olduğunuzdan emin olun.")
            input("Gruba erişiminiz olduğundan emin olduktan sonra ENTER'a basın...")
            driver.get(GROUP_URL)
            time.sleep(5)
        
        # 4. Tüm konuları yükle (scroll)
        scroll_to_load_all_topics(driver)
        
        # 5. Konu linklerini topla
        topic_links = get_all_topic_links(driver)
        
        if not topic_links:
            print("\n❌ Hiç konu linki bulunamadı!")
            print("Sayfa kaynağı kaydediliyor (debug için)...")
            
            # Debug: Sayfa kaynağını kaydet
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            debug_path = os.path.join(OUTPUT_DIR, "debug_page_source.html")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"📁 Debug dosyası: {debug_path}")
            
            # Kullanıcıya sayfadaki elementleri göster
            print("\nSayfadaki tüm linkler:")
            all_a = driver.find_elements(By.TAG_NAME, "a")
            for a in all_a[:30]:
                try:
                    href = a.get_attribute("href") or ""
                    text = a.text.strip()[:50]
                    if href:
                        print(f"  → {text} | {href}")
                except:
                    pass
            
            input("\nDevam etmek için ENTER'a basın (veya Ctrl+C ile çıkın)...")
            return
        
        # 6. Her konuyu kazı
        print(f"\n{'=' * 60}")
        print(f"📚 {len(topic_links)} konu kazınacak...")
        print(f"{'=' * 60}")
        
        all_topics = []
        for i, link in enumerate(topic_links, 1):
            topic_data = scrape_topic(driver, link, i, len(topic_links))
            all_topics.append(topic_data)
            time.sleep(1.5)  # Rate limiting - Google'ı kızdırmamak için
        
        # 7. Önemli mesajları filtrele
        important_topics = filter_important(all_topics)
        
        # 8. Sonuçları kaydet
        print(f"\n{'=' * 60}")
        print("💾 Sonuçlar kaydediliyor...")
        print(f"{'=' * 60}")
        save_results(all_topics, important_topics, OUTPUT_DIR)
        
        # 9. Özet
        print(f"\n{'=' * 60}")
        print("✅ TAMAMLANDI!")
        print(f"{'=' * 60}")
        print(f"📊 Toplam konu: {len(all_topics)}")
        print(f"⭐ Önemli konu: {len(important_topics)}")
        print(f"📂 Çıktı klasörü: {OUTPUT_DIR}")
        
        if important_topics:
            print(f"\n🔝 En önemli 5 konu:")
            for i, t in enumerate(important_topics[:5], 1):
                print(f"  {i}. [{t['match_count']} eşleşme] {t['title'][:60]}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Kullanıcı tarafından iptal edildi.")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Tarayıcı açık bırakılıyor (manuel kontrol için).")
        # driver.quit()  # İsterseniz bu satırı açarak tarayıcıyı kapatabilirsiniz


if __name__ == "__main__":
    main()
