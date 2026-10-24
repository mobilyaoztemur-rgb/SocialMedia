# Kalıcı sosyal hesap erişimi — GitHub ve Cloudflare

## Kullanıcının hedefi

Hesap sahibi sosyal platformlara bir kez giriş yapar. Oturumlar kalıcı tutulur. Kullanıcı bu sohbette talimat verdiğinde ajan, yetkilendirilmiş bir bağlantıyla aynı tarayıcı profillerini kullanır. Gönderi hazırlama/yayınlama ve sonuç kaydı platform bazında uygulanır. Tarayıcı oturumu süresiz garanti edilemez; platformun oturum sonlandırması veya ek doğrulama isteği sahibin müdahalesini gerektirebilir.

BrowserAct profili oluşturuldu ve Facebook giriş ekranı doğrulandı. BrowserAct servis anahtarı kendi yerel kimlik deposunda, repo dışında tutuluyor. Ancak uzaktan kontrol geçidine TCP 9070 bağlantısı hem normal hem genişletilmiş çalıştırma kontrolünde reddedildi. Henüz Facebook girişi veya sayfa yetkisi doğrulanmadı. Aşağıdaki yöntem bu geçide bağımlı olmayan alternatif tasarımdır; dağıtılmış/çalışıyor diye raporlanmamalıdır.

## Önerilen bileşenler

| Bileşen | Rolü |
|---|---|
| GitHub deposu | Uygulama, otomasyon akışları, kurulum ve dağıtım dosyaları |
| GitHub Actions Secrets veya sunucu secret deposu | Gerekli gizli değerleri yetkili dağıtım/çalışma sürecine sağlamak |
| Sürekli erişilebilir VPS veya sahibin açık bilgisayarı | Chrome ve kontrol servisinin çalışması |
| Kalıcı disk/volume | Chrome profilindeki oturumlar, local storage ve cihaz durumunun yeniden başlatmada korunması |
| Cloudflare Tunnel | Kontrol servisini korumalı HTTPS uç noktasına bağlamak; origin makineden Cloudflare'a çıkış erişimi gerekir |
| Cloudflare Access | Sahibin tarayıcı ekranına girişini ve ajanın servis erişimini ayrı yetkilendirmek |
| HTTPS kontrol servisi veya uyumlu uzak MCP | Bu sohbetin mevcut araçlarından tarayıcıya gerçekten erişebilmek |
| Kalıcı iş kuyruğu | Manuel görevler ve planlı yayınların aynı profilde çakışmasını engellemek; sonuçları kaydetmek |

Cloudflare Tunnel kendi başına Chrome çalıştırmaz veya profil saklamaz. Sunucu açıkken tarayıcı gerektiğinde başlatılabilir; oturumun kalıcılığı için Chrome sürecinin sürekli açık olması şart değildir, profil dosyalarının korunması gerekir.

## Erişim akışı

1. Sunucuda ayrı kullanıcı/kapsayıcı ve kalıcı profile sahip Chrome hazırlanır. Kişisel bilgisayarın mevcut ana profilinin tamamı otomasyona açılmaz.
2. Yalnızca hesap sahibinin erişebildiği, kimlik doğrulamalı görsel kontrol ekranı kurulur. Sahip sosyal hesaplara giriş yapar ve MFA işlemlerini tamamlar. Araç, erişim verildikten sonra kullanıcı tamamladığını söyleyene kadar oturuma müdahale etmez.
3. Ajan için HTTPS kontrol uç noktası veya desteklenen bir MCP bağlantısı kurulur. Bu sohbette bir MCP dosyasının repoda bulunması araç eklenmiş olduğu anlamına gelmez. MCP istemcisine gerçek kayıt veya mevcut shell araçlarından erişilebilen, kimlik doğrulamalı HTTPS istemcisi gerekir.
4. Cloudflare Access servis token'ıyla makine erişimi, sahip girişiyle insan erişimi ayrılır. Genel bir Chrome CDP portu internete açılmaz. Token yalnızca doğru hedef alan adına gönderilir.
5. Ajanın bu ortamından sağlık ve yetki testi yapılır. Yetkisiz isteğin reddedildiği, yetkili isteğin doğru profile ulaştığı doğrulanır. Bu geçmeden bağlantı hazır denmez.
6. Birinci platformda yalnızca giriş durumu, doğru hesap ve sayfa yöneticiliği doğrulanır. Sonra diğer platformlar tek tek eklenir. Hesap kurulumunda gönderi yayımlanmaz.
7. Kalıcı profil kapatılıp yeniden açılarak oturumun korunduğu doğrulanır. Daha sonra yeni bir Codex görevinden de erişim test edilir. Her konuşmanın gerekli araç bağlantısı ve yetkilendirmeye sahip olması gerekir.

## GitHub Secrets sınırı

GitHub Secrets içinde parola veya servis anahtarı saklanabilir. Değerler Git içeriği olmaz ve normal depo erişimiyle geri okunamaz. Yetkili bir Actions workflow'u bunları dağıtım/çalışma ortamına aktarabilir. Ajanın repoyu okuyabiliyor olması Secrets değerlerini okuyabileceği veya sosyal hesaba eriştiği anlamına gelmez.

Normal GitHub-hosted Actions işleri geçici çalışma ortamlarında çalışır; bunları kesintisiz Chrome sunucusu olarak kullanmayız. GitHub dağıtım ve gerektiğinde görev tetikleme rolünü üstlenir. Self-hosted runner seçilirse kalıcı makineyi yine bizim sağlamamız gerekir.

Kullanıcı parolaları kullanmayı yetkilendirmiştir; gerektiğinde güvenli secrets üzerinden kullanılabilirler. Fakat parola, kayıtlı tarayıcı oturumunun veya MFA'nın yerine geçmez. İlk bağlantıda hesap sahibinin görsel giriş yapması tercih edilir. Profil ve çerezler düz metin repo dosyası veya açık Actions artifact/cache olarak saklanmaz. Yedekler erişimi kısıtlı ve şifreli tutulur.

## Cloudflare Browser Run alternatifi

Resmi belgeler, aktif oturumların yeniden kullanılabildiğini ancak boşta kalma sınırı ve sürüm dağıtımı gibi nedenlerle tarayıcıların kapanabildiğini belirtiyor. Bu nedenle basitçe bir Worker oluşturup tüm sosyal hesapların kalıcı Chrome profili gibi açık kalacağını varsayamayız. Sunucusuz tasarımda giriş durumunu ayrı, güvenli depolama ile yeniden kurmak gerekir ve tüm platformlarda işe yaradığı test edilmelidir. Bu hedef için VPS/kalıcı makine + Tunnel ilk öneridir.

## Uygulanan PC yolu

Kullanıcı Windows 10/11 bilgisayarı sürekli açık tutabileceğini ve henüz Cloudflare'da alan adı olmadığını belirtti. `woodmood.bridge`, `woodmood.remote`, Windows başlatıcıları ve kaynak ZIP paketleyicisi uygulandı. İlk bağlantı alan adı gerektirmeyen, değişken adresli Quick Tunnel üzerinden denenebilir; origin tüm yollarında Bearer token ister. Cloudflare Access henüz kurulmuş değildir. Teknik adımlar [WINDOWS_SETUP.md](WINDOWS_SETUP.md) içinde.

Servis ve gerçek Chromium işlemleri Linux bulut makinesinde test edildi. Windows başlatıcıları, PC'nin ağ erişimi, sosyal hesap girişleri ve yeni bir görevden gerçek PC'ye erişim henüz doğrulanmadı.

## Henüz gereken bilgiler

- Windows PC kurulumu ve çalışır Quick Tunnel adresi bekleniyor; makine seçimi tamamlandı.
- Kalıcı adres/Access aşamasında Cloudflare alan adı ve Zero Trust erişimi değerlendirilecek; ilk deneme için gerekmiyor.
- Seçilen makinenin gerekli Cloudflare bağlantılarına çıkış erişimi var mı?
- Dağıtım yetkisi nasıl sağlanacak? Gerekli alan adı ve hesap kapsamı belli olmadan geniş yetkili token istenmez.

Bu sohbette Cloudflare API/token ve Access servis değişkenlerinin yalnızca varlığı kontrol edildi; ilgili bağlar bulunmadı. Cloudflare hesabına veya yeni bir sunucuya dağıtım yapılmadı. Ücretli altyapı satın alınmadı. BrowserAct olmadan ilerlemek ayrıca değerlendirilir; mevcut oturum/kimlik dosyaları silinmez.

## Resmi kaynaklar — 24 Ekim 2026

- [GitHub-hosted runner yaşam döngüsü](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners)
- [GitHub Actions Secrets kullanımı](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
- [Cloudflare Access servis token'ları](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/)
- [Cloudflare Browser Run sınırları](https://developers.cloudflare.com/browser-rendering/platform/limits/)
- [Cloudflare tarayıcı oturumlarını yeniden kullanma](https://developers.cloudflare.com/browser-rendering/workers-bindings/reuse-sessions/)
- [Chrome DevTools MCP ve CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp)
