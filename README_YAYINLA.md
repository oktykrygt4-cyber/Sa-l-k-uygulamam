# Kişisel Hekimim 3.0 — İnternet üzerinden çalışan TEST sürümü

Bu proje özgün Python sunucusunu ve hasta/hekim arayüzlerini kullanır. Yalnızca **kurgusal veriyle deneme** içindir. Gerçek hasta verisi, gerçek rapor, kişisel kimlik bilgileri veya klinik karar amacıyla kullanmayın.

## Yayın (Railway)

1. GitHub üzerinde özel bir depo açıp bu klasördeki `server.py`, `static/`, `Dockerfile`, `railway.json`, `.dockerignore` dosyalarını ekleyin. `demo.db` yüklemeyin.
2. Railway > New Project > Deploy from GitHub Repo ile depoyu bağlayın.
3. Railway Service > Variables: `KH_PUBLIC_DEMO=1`, `KH_DB_PATH=/app/data/demo.db`. `PORT` Railway tarafından sağlanır.
4. **İsteğe bağlı**: Verilerin yayın yeniden başlatmasında kaybolmaması için `/app/data` dizinine Railway Volume bağlayın. Yalnızca DEMO veri tutun.
5. Settings > Networking > Public Networking > Generate Domain ile herkese açık HTTPS adresi oluşturun.
6. `/api/health` yolunda `mode: public_demo` yanıtını ve girişten sonra hasta/hekim sayfalarını test edin.

**Demo girişleri:** `hasta@demo.local` ve `hekim@demo.local`; şifre `Demo12345!`. Bu hesaplar paylaşımlıdır: Herkes aynı demo hesabının verilerini görebilir. Gerçek bilgi girmeyin. Kayıt açma, dosya yükleme ve parola değiştirme çevrim içi test modunda kapalıdır.

## Mevcut sınırlar

- Bir medikal ürün, tıbbi yapay zekâ veya gerçek 3D hesaplama servisi değildir.
- Güvenlik incelemesi, kullanıcı/rol izolasyonu, hekim doğrulaması, oran sınırlama, CSRF, veri silme ve depolama politikaları tamamlanmadan gerçek kullanıcılara açılmamalıdır.
- Dış barındırma hizmetinde ücret, kaynak limiti ve uyku politikaları değişebilir.
- GitHub ve Railway hesaplarında oturum açılması gerekir; ZIP kendi başına herkese açık adres üretmez.

## Yerelde çalışma

`KH_PUBLIC_DEMO=0 python server.py` (Windows'ta `UYGULAMAYI_AC.bat`).

## Klasik localhost'tan farkı

`KH_PUBLIC_DEMO=1` iken HTTP sunucusu `0.0.0.0` üzerinde Railway'in `PORT` değerini dinler, HTTPS üzerinden gelen aynı-kaynaklı POST istekleri kabul eder, Secure cookie ayarlar ve tarayıcı açmaya çalışmaz. Veritabanı dosyası `KH_DB_PATH` ile belirlenir.
