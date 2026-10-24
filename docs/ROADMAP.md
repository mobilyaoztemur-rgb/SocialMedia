# Uygulama yol haritası

Amaç: Yeni projeleri düzenli keşfetmek, mevcut arşivi eskiden yeniye tüketmek, projeyi her sosyal platformun biçimine uyarlamak ve paylaşımın sonucunu ayrı ayrı izlemek. Kullanıcı tercihi **tam otomatik paylaşım**; paylaşım sıklığı henüz belirlenmedi. İlk entegrasyon önceliği Instagram, Facebook ve LinkedIn.

## 0 — Hazırlanan temel

- Python 3.12, uv kilit dosyası, FastAPI, SQLite ve yerel Türkçe yönetim paneli.
- Canlı projeler sayfasından URL, başlık, açıklama ve projeye ait orijinal galeri görselleri.
- Kaynak URL ile tekrar tarama; proje/platform başına benzersiz taslak; kaynak özetiyle değişiklik takibi.
- Instagram, Facebook, LinkedIn için ayrı metin şablonları ve görsel çıktıları.
- Otomatik taslak hazırlama, bilinmeyen tarihte manuel sıralama, UTC kayıtlı deneme planları ve işlem geçmişi.
- Dokuz profilin açık adresleri `accounts.toml` içinde; hiçbirine giriş yapılmadı.

## Seçilen bağlantı yolu — kalıcı Chrome

Kullanıcı API geliştirici kaydı yerine kalıcı tarayıcı oturumuyla ilerlemeyi seçti. Önce Facebook sahibi uzaktan giriş yapacak ve sayfa erişimi doğrulanacak. Ardından Instagram, LinkedIn ve diğer platformlar sırayla eklenecek. Profil ve başlangıç ayrıntıları [BROWSER.md](BROWSER.md) içinde. Aşağıdaki API planı alternatif yol olarak korunuyor; tarayıcı hesabı bağlamanın önkoşulu değil.

Kesin proje sırası: **Azerbaycan → Fırat Serhat Motors → Mormenekşe → Northernland**. Yeni keşfedilen projeler sona eklenir. Kural konfigürasyona ve gerçek kataloğa işlendi.

## 1 — Alternatif API yolu: Instagram, Facebook ve LinkedIn'de ilk gerçek yayın

**Önce gerekenler:** Facebook Sayfası, Instagram hesabının profesyonel/işletme yayınlama uygunluğu ve bağlantıları, LinkedIn şirket sayfası yönetici yetkileri. İlgili geliştirici uygulamaları, ürün erişimleri, OAuth izinleri ve gerektiğinde uygulama incelemeleri gerçek hesaplar üzerinden doğrulanacak. Profil URL'si bu şartları kanıtlamaz.

1. Meta ve LinkedIn OAuth bağlantı akışlarını ekle. Uygulama kimlikleri, sayfa/kuruluş kimlikleri ve erişim/yenileme bilgilerini secret deposundan okut. Panelde izin kapsamı, süre sonu ve yeniden bağlantı gereksinimini göster.
2. Ayrı platform yayınlayıcıları uygula. Görsel sayısı, carousel biçimi, dosya sınırları, yükleme adımları ve hesap bazlı güncel API erişimi resmi belgelerle doğrulansın. Instagram için gerekiyorsa platformun erişebildiği HTTPS medya URL'leri sağlansın; yerel `var/media` yolları kullanılamaz.
3. İçerik politikasını netleştir: ilk sıradaki projeler, marka dili, Türkçe/diğer diller, hashtag ve CTA tercihi, her projeden kaç gönderi çıkarılacağı, görsel sırası. İlk şablonlar içerik uydurmaz; istenirse yapılandırılmış marka kurallarıyla LLM eklenir.
4. Sıklık, ilk yayın saati, aktif günler, saat dilimi ve ağlar arasındaki zaman farkını belirle. Bu karar gelmeden canlı worker gönderi başlatmasın. Yeni projeler mevcut arşivin neresine girecek kuralını tanımla; değişen görseller otomatik yeniden paylaşılmasın.
5. Bir projeyi üç platformda uçtan uca doğrula. Platformun döndürdüğü gönderi kimliği, gerçek bağlantısı ve işlem sonucu saklansın. Hata durumunda “yayımlandı” kaydı oluşmasın.
6. Kalıcı yayın kuyruğu/outbox, iş kiralama, token yenileme, sınırlandırılmış ve gecikmeli tekrar deneme ekle. İstek zaman aşımında platformda gönderinin oluşup oluşmadığı araştırılmadan kör tekrar yapılmasın. Mevcut benzersiz taslak satırı, tek başına ağ üzerinden tam bir kez yayın garantisi vermez.

Başarı ölçütü: Hesap bağlantıları ve zamanlaması tanımlı sistem, sıradaki tek projeyi üç platformda yayımlar; süreç yeniden başlatılınca ikinci kez göndermez, bir platform hatası diğerlerinin sonucunu kaybettirmez. Sonrasında onaysız otomatik çalışma etkinleştirilir; kullanıcı istediğinde durdurabilir.

Resmi başlangıç kaynakları (uygulama sırasında güncel gereksinimler kontrol edilecek):

- https://developers.facebook.com/docs/instagram-platform/
- https://developers.facebook.com/docs/pages-api/
- https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

## 2 — Pinterest, Threads, Tumblr ve X

| Platform | İçerik yaklaşımı | Bağlantı/erişim işi |
|---|---|---|
| Pinterest | Proje/oda bazlı dikey görsel, pano, siteye yönlendiren Pin | Uygulama/OAuth, uygun hesap ve hedef pano kimliği |
| Threads | Kısa proje hikâyesi, görsel dizisi | Threads uygulaması, hesap yetkilendirmesi ve API erişimi |
| Tumblr | Uzun açıklama, görsel seti, etiketler | OAuth ve hedef blog yetkisi |
| X | Kısa metin, görsel, proje bağlantısı | API planı/ücreti, medya yükleme ve yazma izinleri |

Bu platformların adresleri kaydedildi; taslak üreticileri ve yayınlayıcıları henüz uygulanmadı. Her biri kendi kota ve dosya sınırlarıyla eklenecek. API planı gerektiren hizmetler için ücret varsayımı veya satın alma yapılmadı.

## 3 — YouTube ve TikTok

YouTube için videoya dönüşüm gerekir; TikTok tarafında video yanında desteklenen fotoğraf yayın akışı da değerlendirilebilir. Video akışı: proje görsellerinden 9:16 kısa video, kontrollü geçişler, metin bindirmeleri, lisanslı müzik veya sessiz çıktı ve platforma özel başlık/açıklama. Video kalitesinin ilk kontrolünden sonra tam otomatik üretim yapılabilir.

YouTube ve TikTok için OAuth, yükleme/yayın API erişimi, kota ve gerektiğinde uygulama denetimleri ayrı doğrulanacak. Her hesabın otomatik genel yayına erişimi olacağı varsayılmıyor. İşlem maliyeti nedeniyle video render işleri ayrı kuyruğa taşınacak.

## 4 — Kesintisiz işletim ve sosyal medya kontrolü

- Her zaman açık bir sunucu veya yönetilen worker; web, tarama ve yayın süreçleri supervisor ile yeniden başlatılabilir olsun. Codex oturumunun açık kalmasına güvenilmesin.
- Başlangıçta tek worker ve kalıcı SQLite diski yeterli; çoklu worker/çoklu müşteri ihtiyacında PostgreSQL + kalıcı iş kuyruğuna geçilsin. Medya için S3 uyumlu nesne deposu ve HTTPS servisleme eklensin.
- Gerçek yönetim paneline kullanıcı girişi, HTTPS, rol bazlı işlem yetkisi ve erişim kayıtları ekle. Mevcut panel yalnızca loopback geliştirme kullanımı içindir.
- Veritabanı ve medya yedekleme, geri yükleme denemesi, tarama/yayın hatası uyarıları, token süresi takibi, kota görünürlüğü, acil durdurma ve ayrı platform devre dışı bırakma.
- İlk işletim bütçesi: sunucu + medya depolama; tercihe bağlı LLM/video maliyeti; ilgili sosyal ağların API ücretleri. Platformlar doğrulanmadan tutar taahhüdü yok.
- Sonraki kapsam: gönderi bağlantılarından performans takibi; platform izinleri elveriyorsa yorum/mesajların tek gelen kutusunda toplanması. İlk sürümde yorumlara veya mesajlara otomatik yanıt verilmez.

## Bir sonraki kararlar

1. Proje sırası belirlendi ve kaydedildi; bu karar artık beklemiyor.
2. İlk canlı paylaşım tarihi ve sıklığı. Sitenin 6 saatte bir taranması yayın sıklığı anlamına gelmez.
3. BrowserAct hesap bağlantısı ve önce Facebook için tarayıcıda tek seferlik sahip girişi; ardından diğer platformlar.
4. Önce yalnızca görsel içerik mi, yoksa video aşaması da hemen mi önceliklendirilecek?

Sıralama hazırdır. Paylaşım sıklığı, hesap bağlantıları ve platform yayın akışlarının uygulanması canlı yayına geçiş için gereklidir. Altyapının mevcut geliştirme özellikleri hesap şifreleri olmadan çalışır.
