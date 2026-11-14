KİŞİSEL HEKİMİM 3.0 — TEK UYGULAMA / YEREL ÇALIŞAN GELİŞTİRME SÜRÜMÜ
=====================================================================

BAŞLATMA (WINDOWS)
1. ZIP dosyasını ayrı bir klasöre tamamen çıkarın.
2. Python 3.10 veya üstü kurulu olmalı. Python kurulurken PATH seçeneğini açabilirsiniz.
3. UYGULAMAYI_AC.bat dosyasını çift tıklayarak açın.
4. Tarayıcı kendiliğinden açılmazsa siyah penceredeki http://127.0.0.1:PORT adresini ziyaret edin.
5. Çıkış yapmak için uygulamadaki Çıkış Yap düğmesini; sunucuyu durdurmak için açılan komut penceresinde Ctrl+C kullanın.

BAŞLATMA (MAC / LINUX)
Terminalde uygulama klasöründe: python3 server.py

İLK AÇILIŞTA DENEME HESAPLARI
Hasta: hasta@demo.local   Şifre: Demo12345!
Hekim: hekim@demo.local   Şifre: Demo12345!
Giriş ekranındaki Hasta / Hekim Kayıt Ol bağlantılarıyla yeni deneme hesapları açabilirsiniz.

NELER ÇALIŞIR?
- Tek açılış ekranı, Hasta Girişi, Hekim Girişi, kayıt olma, çıkış ve parola değiştirme.
- Hasta: AI sohbeti yerel taslak arayüzü, beş adımlı check-up, sağlık profili,
  kayıtlar, dosya notları, örnek dosya yükleme, randevu ve uzman görüşü talebi.
- Hekim: ana panel, vaka oluşturma, klinik notlar, vaka bazlı sohbet notu,
  örnek renkli görüntü katmanları, senaryo A/B/C planlama notları, vaka belgeleri,
  hekim ve hasta profilleri, hekim rehberi, bağlantı istekleri, konsültasyon
  talebi / kabul / metin yanıtı, rapor taslakları, randevular, çalışma saatleri,
  bildirimler, tema ve metin boyutu ayarları.
- Hasta talebi seçilen yerel hekimin Bildirim Merkezi'ne düşer ve durum değişiklikleri
  hasta hesabına yansır.
- Bir hekim başka bir hekim hesabına örnek konsültasyon talebi gönderebilir.
  Alıcı kabul veya reddedebilir; kabul ettiğinde metin yanıtı gönderebilir.
- Birden çok hekim hesabının vaka, not ve belge kayıtları ayrıdır.
- Tüm kayıtlar uygulama klasöründeki demo.db SQLite veritabanında tutulur.
- Deneme belgeleri yalnızca dosyanın sahibi hesaptan açılabilir.
- Arayüz telefon, tablet ve masaüstünde duyarlı çalışacak biçimde hazırlanmıştır.

DİKKAT — ÇOK ÖNEMLİ
Bu program GELİŞTİRME / DENEME SÜRÜMÜDÜR. Gerçek hasta veya gizli sağlık verileri
GİRMEYİN. Sağlık Bakanlığı yetkilendirmesi, KVKK uygunluk değerlendirmesi,
profesyonel kimlik doğrulaması, klinik yazılım doğrulaması ve elektronik imza YOKTUR.
Bu yazılım hastalık tanısı koymaz, gerçek klinik karar vermez, kılavuz tarayıp
kesin öneri üretmez; CBCT/DICOM segmentasyonu veya tıbben geçerli 3D cerrahi
simülasyon yapmaz. Görüntü üstündeki renkli işaretlemeler YALNIZCA TEMSİLİDİR.
"Çevrim içi" göstergesi yalnızca arayüz görünümüdür; gerçek kullanılabilirlik değildir.
Açılış görselindeki "KVKK uyumlu" yazısı onaylı görsel tasarım öğesidir; bu
sürüm için hukuki veya teknik uygunluk belgesi ANLAMINA GELMEZ.
Hasta dosyaları hekimler arasında otomatik paylaşılmaz. Yerel konsültasyon için
yalnızca kullanıcının girdiği kurgusal soru metni iletilir.

VERİ YÖNETİMİ
- Gerçek veriler GİRMEYİN.
- Deneme verileri uygulamanın yanındaki demo.db dosyasında oluşur.
- Verilerinizi yedeklemek için VERILERI_YEDEKLE.bat dosyasını kullanın.
- Temiz başlangıç için uygulamayı kapatın ve demo.db dosyasını yeniden adlandırın
  (önce yedeğini alın). Bir sonraki başlangıçta yeni deneme veritabanı oluşturulur.
- Başka bilgisayara taşımak için klasörle birlikte demo.db dosyasını da taşıyın.

TEKNİK
- Python 3 standard library (başka pip kurulumu gerektirmez).
- Yerel HTTP sunucu: 127.0.0.1, varsayılan 8765 portu; doluysa takip eden portlar.
- Veritabanı: SQLite.
- Ağ üzerinden paylaşım / bulut servisi kurulumu yapılmaz.
- Sunucuya erişim yerel makine ile sınırlıdır; yine de bu bir üretim güvenlik çözümü değildir.

Bu paket daha önce onaylanan giriş görselini ve hasta/hekim tasarımını içerir.


YENI TASARIM (14 Kasim 2026)
- Giris ekrani gercek HTML kartlarla yeniden tasarlandi. Iki kez giris dugmesi yoktur.
- Hasta ve hekim giris/kayit formlari yenilendi.
- Hekim ana paneli kartlari daha belirgin hale getirildi.
- Chrome eski ekran goruntusunu gosterirse CTRL+SHIFT+R yapin.
- Eski kayitlari kullanmak icin yedekli demo.db dosyanizi bu klasore kopyalayabilirsiniz.
