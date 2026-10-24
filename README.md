# Woodmood Social

Woodmood projelerini arşivleyen, platforma özel içerik ve görsel hazırlayan, eskiden yeniye deneme yayın planı oluşturan geliştirme altyapısı.

**Mevcut durum:** Canlı siteden 4 proje alındı. Instagram, Facebook ve LinkedIn için 12 ayrı metin taslağı üretildi. Dokuz sosyal hesap tanımlı. BrowserAct giriş devri ağ engeline takıldı. Seçilen yeni yol Windows PC üzerinde kendi Chrome kontrol servisimiz; sosyal hesap girişleri bekleniyor. Gerçek sosyal ağ paylaşımı henüz uygulanmadı. Bu sürüm hiçbir sosyal ağa gönderi göndermez.

## Seçilen kalıcı bilgisayar bağlantısı

Windows 10/11 bilgisayarı kalıcı Chrome makinesi olarak kullanıyoruz. Alan adı henüz yok; ilk test için Cloudflare Quick Tunnel ve uzun Bearer anahtarı kullanan ayrı kontrol servisi hazırlandı. BrowserAct gerekmez. **Gerçek PC bağlantısı ve sosyal hesap girişleri henüz doğrulanmadı.**

[Windows kurulum adımları](docs/WINDOWS_SETUP.md): `scripts\pc\setup.cmd`, `start-bridge.cmd`, girişlerden sonra `agent-ready.cmd` ve ayrı terminalde `start-tunnel.cmd`. Sahip kendi girişini yaparken ajan erişimi otomatik olarak durur. Kalıcı profil ve anahtar `%LOCALAPPDATA%\WoodmoodSocial` içinde saklanır.

Kontrol istemcisi `python -m woodmood.remote` ile bu bulut ortamından HTTPS üzerinden kullanılabilir. Yeni bir MCP kaydı eklemek zorunlu değildir. Gerçek tünel adresi ve anahtarı geldiğinde bağlantı ayrıca test edilecek. Kaynak kurulum paketi `python scripts/package-pc.py` ile `dist/` altında üretilir; sır ve profil içermez.

Bu altyapı platform ekranlarını kullanmaya temel sağlar; platforma özel otomatik yayın akışları ve paylaşım sıklığı henüz tamamlanmadı.

## Kurulum

Python 3.12 ve `uv` kullanılır. Çalışma dizini `/workspace/SocialMedia`.

```bash
uv sync --frozen --extra browser
uv run --frozen python -m woodmood init
uv run --frozen --extra browser pytest -q
uv run --frozen python -m woodmood serve
```

Sunucu yalnızca loopback üzerinde 8000 portuna bağlanır. Bu bir yerel geliştirme panelidir; internetten erişilen bir yönetim paneli olarak dağıtılmamalıdır. API şeması `/api/docs`, sağlık kontrolü `/health`, panel `/` yolundadır. Kimlik doğrulama ve HTTPS, üretim dağıtımı aşamasında eklenecektir.

Ayrı bir terminalde kaynak taraması ve taslak üretimi:

```bash
uv run --frozen python -m woodmood scan
uv run --frozen python -m woodmood drafts
uv run --frozen python -m woodmood worker
```

`worker` başlangıçta ve her 6 saatte siteyi tarar, yeni projelere taslak üretir. Bu süre **tarama sıklığıdır**, paylaşım sıklığı değildir. İşlem kapandığında tarama durur. Codex oturumunun veya bulut ortamının yayına alınmasının bu süreci sürekli çalışır tutacağı varsayılmaz. Kesintisiz çalışma için yol haritasındaki yönetilen sunucu/worker dağıtımı gerekir.

Kaynak değişince mevcut taslaklar ve eski deneme planı geçersizleşir; metinler korunur. Kaynak bilgisiyle yenilemek için (elle düzenlenmiş metinlerin üzerine yazar):

```bash
uv run --frozen python -m woodmood drafts --refresh
```

## İlk kullanım

1. Panelden siteyi tarayın; dört mevcut projenin ve kendilerine ait görsellerin geldiğini kontrol edin.
2. Kullanıcının belirlediği sıra `config.toml` içine kaydedildi: **Azerbaycan → Fırat Serhat Motors → Mormenekşe → Northernland**. Yeni projeler keşif sırasıyla sona eklenir; kaynak tarihi veya sitenin liste sırası bu kuyruğu değiştirmez.
3. Üç platformun taslaklarını inceleyin. `automatic` mod yeni taslakları kendiliğinden hazır yapar; düzenlediğiniz taslağı tekrar hazır olarak işaretleyebilirsiniz.
4. Panelden görselleri hazırlayın. Proje açılışı ve galerisindeki **orijinal** görseller kullanılır. “Diğer projeler” kartları, menü ve logo dışarıda bırakılır.
5. İsterseniz başlangıç, saat aralığı ve proje sayısını açıkça girerek **deneme** planı oluşturun. Tarihler işletmenin `Europe/Istanbul` zaman diliminde girilir ve veritabanında UTC saklanır. Paylaşım sıklığına varsayılan atanmadı.

Alternatif deneme planı komutu; tarih ve aralığı kendi kararınıza göre değiştirin:

```bash
uv run --frozen python -m woodmood plan \
  --first-at '2099-01-01T12:00:00+03:00' --interval-hours 48 --count 1
```

Bu komuttaki tarih ve aralık yalnızca kullanım örneğidir. Planlar `simulation_only` olarak saklanır; gönderi statüsü hiçbir zaman “yayımlandı” olmaz. Planlar `/api/plans/{id}` ile JSON olarak alınabilir. Panelden planı iptal etmek, metinleri koruyup tekrar düzenlemeye açar. Kaynak değişince geçmiş plan JSON'u denetim kaydı olarak kalır; aktif durum `/api/state` içindedir.

## Dosyalar ve veri

- `config.toml`: Kaynak URL, doğrulanmış seçiciler, tarama aralığı, ilk üç platform ve çalışma modu.
- `accounts.toml`: Kullanıcının sağladığı dokuz **açık** profil adresi. Profil adresi eklemek hesabı bağlamaz.
- `woodmood/`: FastAPI paneli, SQLite kayıtları, kaynak toplayıcı, içerik üretimi, görsel hazırlama, deneme planlayıcı ve tarama worker'ı.
- `var/woodmood.sqlite3`: Gerçek proje, taslak, plan ve işlem kayıtları. Git dışında tutulur.
- `var/media/{proje}/{kaynak-özeti}/`: Kaynağa göre sürümlenmiş yerel JPEG çıktıları. Git dışında tutulur.
- `tests/fixtures/`: Açıkça işaretlenmiş yapay test verileri; uygulama bu verileri kendiliğinden içeri almaz.
- [Tarayıcı bağlantısı](docs/BROWSER.md), [yol haritası](docs/ROADMAP.md), [mimari](docs/ARCHITECTURE.md), [doğrulama kaydı](docs/VALIDATION.md).

Metinler şu anda kaynaktaki gerçek bilgilerden sabit Türkçe şablonlarla üretilir. Yapay zekâ metin yazımı, görsel kalitesi seçimi, carousel sınırlarına göre bölme, video üretimi ve sosyal ağ API doğrulaması sonraki aşamadır. Görsel dosyaları platforma uygun başlangıç ölçülerine dönüştürülür; mobilya kırpılmaz, gerektiğinde nötr zemin eklenir. Deneme planı orijinal görsel URL'lerini ve hedef ölçülerini saklar; yerel görsel hazırlığının tamamlandığını veya platformun dosyaları kabul ettiğini iddia etmez.

## Erişim ve sırlar

Hesap şifreleri, OAuth erişim/yenileme token'ları, tarayıcı çerezleri ve gerçek `.env` dosyaları Git'e yazılmaz. GitHub Secrets uygulama sunucusuna kendiliğinden aktarılmaz; dağıtımda güvenli aktarım gerekir. Seçilen bağlantı yöntemi kalıcı Chrome oturumudur. İlk giriş ve iki aşamalı doğrulama hesap sahibi tarafından yapılır; oturum süresi dolarsa yeniden giriş gerekir. API/OAuth gelecekte alternatif olarak eklenebilir.

Mevcut sürüm herhangi bir sosyal ağ anahtarı istemez. Gerçek bağlayıcılar uygulanırken gerekli alanlar ve hedef API alan adları belirlenecek; değerler bulut ortamının güvenli secret ayarlarından sağlanacaktır. TLS doğrulaması açıktır, her yönlendirmede kaynak alan adı kontrol edilir, bilinmeyen sitelerden dosya indirilmez. Medya ileride CDN'e taşınırsa bu alan adı açıkça kaynak ve ortam izin listesine eklenmelidir.

## Sınırlar

Bu sürüm geliştirme ve içerik hazırlama temelidir. Canlı yayınlayıcı, yorum/mesaj yönetimi, performans istatistikleri, video üretimi, zamanlanmış sosyal ağ gönderimi ve çok kullanıcılı giriş henüz yoktur. Tüm sosyal hesaplar panelde “bağlı değil” görünür. Otomatik paylaşımın canlıya alınması için yol haritasındaki hesap bağlantıları, sıklık kararı ve üretim worker'ı tamamlanmalıdır.

## Seçilen tarayıcı yöntemi

Başlangıç ve giriş akışı [docs/BROWSER.md](docs/BROWSER.md) içinde. `browser.toml` yalnızca herkese açık profil referanslarını içerir. Oturum dosyaları repo dışında tutulur. Tarayıcı bağlantısı hesap kurulumu aşamasındadır; uygulama panelindeki hesaplar doğrulanana kadar bağlı gösterilmez.
