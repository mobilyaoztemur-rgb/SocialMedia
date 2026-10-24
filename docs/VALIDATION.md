# Doğrulama kaydı — 24 Ekim 2026

Bu kayıt mevcut bulut makinesindeki sonuçları anlatır. Yeni görevde snapshot geri yükleme veya gerçek sosyal ağ yayını testi değildir.

## Geçen kontroller

- Python 3.12.14 ile `uv sync --frozen` tamamlandı. Aynı kurulum ve veritabanı başlatma adımları ikinci kez çalıştırıldı; 4 proje ve 12 taslak korundu.
- `uv run --frozen pytest -q`: **32 test geçti**, başarısız/atlanan test yok. TestClient bağımlılığından bir deprecation uyarısı var; testler tamamlandı.
- `node --check woodmood/static/app.js`: başarılı.
- Gerçek çalışan sunucuda `/health`, `/`, `/app.js`, `/style.css`, `/api/state`: HTTP 200. Sunucu yeniden başlatılıp yeni kaynak seçicileriyle tekrar doğrulandı.
- Canlı kaynak: `https://woodmoodmobilya.com/tr/projeler`. Dört proje ve **35 özgün proje görseli** alındı:

| Proje | Görsel | Kaynak açıklamasındaki yıl |
|---|---:|---|
| Northernland Grand Sapphire Penthouse | 13 | Belirtilmiyor |
| Mormenekşe Konut Projesi | 6 | Belirtilmiyor |
| Fırat Serhat Motors Ofis ve Resepsiyon | 5 | 2026 |
| Azerbaycan Konut Projesi | 11 | 2014 |

Bu tablodaki sıra tarama sırasıdır; eskiden yeniye sıralama iddiası değildir. Dört sayfada da makinece okunabilir `datePublished` bulunmadı.

- Daraltılmış canlı DOM seçicileriyle menü, logo, başka proje kartları ve bu kartların açıklamaları dışlandı. Açılış ve galeri orijinal görselleri toplandı.
- Instagram, Facebook, LinkedIn için **12 metin taslağı** oluşturuldu. Sürüm sabit şablon kullanıyor; LLM servisi kullanılmadı.
- Canlı kaynak görsellerinin tamamından **105 JPEG** hazırlandı. Üç platformun her dosyasında boyutlar açılıp doğrulandı; örnek bir gerçek Instagram çıktısı görsel olarak da incelendi.
- Değişmeyen canlı kaynağın yeniden taraması: `added=0`, `changed=0`, `seen=4`; ek taslak yok.
- Gerçek veri üzerinde tarih/sıra eksikken plan isteği HTTP 400 ile durdu; hiçbir gerçek projeye tahminî sıra veya yayın saati atanmadı.
- Ayrı tarama worker'ı çalıştırıldı; ilk canlı tarama başarıyla tamamlandı ve yeni/mükerrer kayıt oluşturmadı.
- Otomatik testler: sayfalama, kısmi kaynak hatasının atomikliği, dış alan adına yönlendirme engeli, orijinal görsel seçimi, eski proje sırası, elle düzenlenen metnin korunması, kaynak değişiminde planın geçersizleşmesi, eşzamanlı planlayıcı, deneme planı iptali, görsel ölçüleri ve API akışı.
- `var/`, medya, veritabanı, `.env` ve sanal ortam Git dışında. Başlangıç deposunda izlenen uygulama dosyası yoktu; mevcut kullanıcı dosyası silinmedi.

## Ortam taslağı

Kurulum betiği (`install_script`), web/tarama worker başlangıç ve hazır olma talimatları (`start_skill`) kaydedildi. Özel ağ izinlerine `woodmoodmobilya.com` ve `www.woodmoodmobilya.com` eklendi; paket yöneticisi preset'i korundu. İlk ağ engeli ayarın çalışma ortamına ulaşmasıyla giderildi ve gerçek işlem tekrar başarılı çalıştırıldı. Sosyal platform sırrı eklenmedi: bu sürümde bunları kullanan yayın bağlayıcısı yok.

Kaydetme, yayımlama değildir. Kullanıcı ortam ayarlarında taslağı inceleyip kaydettikten sonra ortamı yayımlayabilir. Yeni görevde dosyaların geri yüklenmesi bağımsız olarak denenmedi. Çalışan süreçler yeni ortamda yeniden başlatılmalıdır.

## Henüz yapılmayanlar

- OAuth bağlantısı, platform uygulama erişimlerinin doğrulanması ve gerçek gönderi gönderme.
- Gerçek hesaplarda API medya kabulü, carousel veya video testi.
- Üretim yönetim paneli kimlik doğrulaması, kesintisiz barındırma, yayın outbox'ı ve token yenileme.
- Eksik proje tarihleri/yayın sırası ve kullanıcı tarafından belirlenmiş paylaşım sıklığı.

Bu eksikler geliştirme altyapısını kullanmayı engellemez; tam otomatik sosyal ağ yayınına geçiş için tamamlanmalıdır.

## Sonraki aşama — kendi Windows PC bağlantımız

Kullanıcı sürekli açık Windows 10/11 bilgisayar kullanmayı seçti; henüz Cloudflare alan adı yok. BrowserAct uzaktan giriş geçidine erişim sağlanamadığından bağımsız HTTPS kontrol servisi ve istemci eklendi.

- Kilitli `browser` extra'sı: Playwright, sistem Chrome/Chromium ile kalıcı profil açar. Windows varsayılanı görünür Chrome ve açık sandbox'tır; Linux kapsayıcı testinde sandbox kapatma yalnızca ayrı test profillerinde kullanıldı.
- Başlangıçta 34 mevcut test korunarak yeni bridge testleri eklendi. Bir tam çalıştırmada 66 test geçti; paket doğrulaması eklendikten sonra bridge grubunda **33 test** geçti. Korunan 34 uygulama testiyle toplam **67 test** bulunuyor. Paket ve browser testleri gerçek Chromium işlemleriyle tamamlandı; fixture sayfası sentetik olarak işaretlidir.
- Gerçek HTTP sunucusu ayrı cloud doğrulama profiliyle başlatıldı. Aynı HTTPS kontrol istemcisi sınıfının açıkça loopback için izin verilen test modu ile auth sağlık, anahtarsız 401, sahip modunda 423, yerel devir sonrası sayfa listesi doğrulandı. Bu, internetten Windows PC'ye erişim testi değildir.
- Gerçek Chromium'da DOM okuma, metin doldurma, tıklama, dosya seçme ve PNG ekran görüntüsü; yeniden başlatmada sentetik cookie/localStorage kalıcılığı doğrulandı. Sahip modunun mevcut sayfa okumalarını ve eylemlerini engellediği test edildi.
- İşlem anahtarı tekrarında aynı tıklamanın yeniden uygulanmadığı, farklı istekle aynı anahtarın reddedildiği, yarım kalan eylemin yeniden başlatmada `uncertain` kaldığı doğrulandı. Bu, platformdan bağımsız tam bir kez yayın garantisi değildir.
- Kaynak paketi allowlist ile üretildi; `.env`, var/, kişisel profil, `.git`, anahtar ve sanal ortam dışlandı. Windows başlatıcılara ZIP içinde CRLF uygulandı, SHA-256 dosyası üretildi.
- Cloudflared 2026.10.3 resmi GitHub release varlığından alındı ve yayıncının SHA-256 digest'iyle doğrulandı. Linux CLI yardımında Windows scriptindeki Quick Tunnel bayraklarının kabul edildiği kontrol edildi. Tünel oluşturulmadı, Cloudflare hesabında değişiklik yapılmadı ve ücretli ürün açılmadı.
- Windows `.cmd` dosyaları, isteğe bağlı Windows Görev Zamanlayıcı scripti ve GitHub Actions workflow'u ilgili platformlarda henüz çalıştırılmadı. Windows'ta Chrome'un açılması, PC'nin Cloudflare'a ulaşması, gerçek hesap girişleri ve bu sohbetten gerçek PC'ye erişim dış doğrulama bekliyor.
- İlk Quick Tunnel adresi süreç yeniden başlayınca değişebilir. Cloudflare Access SSO bu deneme yolunda kurulmadı; origin servisinin uzun Bearer anahtarı tüm API yollarında zorunludur.

GitHub için CI dosyasına ek olarak yalnızca elle başlatılan `remote-status.yml` hazırlanmıştır; gerekli secret/variable bağlarını ortam değişkenlerine aktararak içerik veya anahtarları loglamadan sağlık kontrolü yapar. GitHub üzerinde çalıştırılmamıştır. Kaynak dosyaları henüz bu görev tarafından GitHub'a push edilmemiştir.
