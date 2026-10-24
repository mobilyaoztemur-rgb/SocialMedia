# Kalıcı tarayıcı bağlantısı

Kullanıcı sosyal hesapları API yerine kalıcı Chrome oturumuyla bağlamayı seçti. İlk hesap Facebook; ardından diğer sekiz platform sırayla bağlanacak. Bu tercih geliştirici uygulaması oluşturmayı ilk bağlantı için zorunlu olmaktan çıkarır.

## Şu anda tamamlananlar

- BrowserAct CLI 1.4.5 ve Chromium mevcut; `scripts/install-browser.sh` tekrarlanabilir araç kurulumudur.
- `woodmood-social` adlı bağımsız Chrome profili oluşturuldu. Genel referanslar `browser.toml` içinde.
- Profil `/workspace/.local/share/browseract/profiles/` altında, Git checkout'ının dışında tutuluyor. Yerel bilgisayardan profil veya çerez alınmadı.
- Gerçek Facebook giriş sayfası açıldı ve giriş alanları doğrulandı. Henüz giriş yapılmadı ve sayfa yöneticiliği doğrulanmadı.
- Sahibine giriş ekranını devretmek için `remote-assist` çağrıldı. Araç bu özellik için BrowserAct hesap bağlantısı istedi. Sahip kaydı tamamladı; auth poll başarılı ve CLI api_key durumu configured olarak doğrulandı. Facebook girişinin sahibine devredilmesi sıradaki adımdır. Kimlik doğrulama sonrası remote-assist yeniden denendi; 230414 hatasıyla hk-relay.browseract.com ve hk-relay-normal.browseract.com geçitlerinin 9070 portuna bağlantı kurulamadı. Kontrol bağlantısı üretilemedi. Doğrudan TCP denemeleri reddedildi; proxy üzerinden HTTPS denemesinde beklenmeyen protokol yükseltme yanıtı alındı. Bu hata ödeme veya abonelik isteği değildi. Ağ/taşıma uyumluluğu çözülmeden sahibin bu tarayıcıda giriş yapabileceği iddia edilmemelidir. Tek kullanımlık bağlantı ve anahtarlar bu belgeye yazılmaz.

## Çalıştırma

Mevcut tarayıcıyı tekrar oluşturmayın. Önce BrowserAct becerisini ve CLI'nın core/advanced talimatlarını okuyun. Oluşturulan profilin ID'si `browser.toml` içinde. Oturum adı kalıcı canlı bağlantı değildir. Başka bir konuşmanın oturumuna dokunmayın.

```bash
cd /workspace/SocialMedia
bash scripts/install-browser.sh
bash scripts/browser-act.sh --version
bash scripts/browser-act.sh browser list
```

Yeni çalışma ortamında veya eski daemon sertifika hatası verdiğinde, gerekli `/home/agent/.pki` yazma iznini aldıktan sonra **aynı shell çağrısında**:

```bash
python scripts/prepare-browser-trust.py
bash scripts/browser-act.sh daemon restart
bash scripts/browser-act.sh --session woodmood-facebook-onboarding browser open \
  chrome_local_125440600169251023 https://www.facebook.com/
```

Daemon yeniden başlatma aktif tarayıcı işlerini etkileyebilir. Sahibi uzaktan giriş yaparken çalıştırmayın; önce mevcut işlemleri ve oturum sahipliğini kontrol edin. Bu üçlü başlangıç yolu mevcut makinede aynı komutlarla test edildi. Sertifika hazırlığı yalnızca sistemin zaten güvendiği kökleri NSS'e ekler. TLS kontrolünü kapatan bayraklar kullanılmaz.

Bu bulut kapsayıcısında Chromium'un setuid ve user-namespace sandbox yöntemleri kullanılamadı. `scripts/chrome/google-chrome` mevcut kapsayıcı izolasyonu içinde `--no-sandbox --disable-dev-shm-usage` ile sistem Chromium'unu başlatır. Bu, tarayıcının kendi sandbox'ının kapalı olduğu anlamına gelir; bu başlatıcıyı kişisel bilgisayarda veya izole olmayan üretim sunucusunda kullanmayın. Üretim dağıtımında tarayıcıya ayrı kullanıcı/kapsayıcı ve uygun sandbox sağlanmalıdır. Sertifika doğrulaması açıktır.

## Sahibin giriş yapması

BrowserAct hesabı bağlandıktan sonra `auth poll` ile doğrulayın. Bir anahtar dönerse değerini çıktıya veya konuşmaya basmayın; yalnızca başarı durumunu bildirin. Sosyal hesap şifresi istemeyin. Facebook oturumu açık değilse yalnızca bu konuşmanın oturumunu açın; giriş durumunu ekrandan kontrol edin.

```bash
bash scripts/browser-act.sh --session woodmood-facebook-onboarding remote-assist \
  --objective 'Woodmood owner signs in to Facebook and completes verification; no publishing'
```

Gerçek uzaktan erişim bağlantısı döndüğünde sahibine verin ve yanıtını bekleyin. Sahibi giriş yaparken oturumda state, screenshot, navigate, network yakalama veya başka tarayıcı komutu çalıştırmayın. Sahibin tamamladığını söylemesinden sonra Woodmood sayfasını ve yönetim ekranı erişimini doğrulayın. Başka kişisel hesapların içeriklerini taramayın; çerez veya oturum dosyası dışarı aktarmayın.

## Sonraki adımlar

1. Facebook girişini ve `mobilyawoodmood` sayfasında işlem yetkisini doğrulama.
2. Instagram ve LinkedIn'i, ardından kalan platformları aynı yöntemle bağlama; her birinde hedef hesap kimliğini doğrulama.
3. Proje/gönderi hazırlama akışını her sitenin güncel ekranlarıyla geliştirme ve doğrulama.
4. Paylaşım sıklığını belirleyip görev başlatıcısı ile yayın sonucunu kaydeden kalıcı iş akışını kurma.

Bir MCP/BrowserAct bağlantısının çalışması, gözetimsiz yayın sisteminin tamamlandığı anlamına gelmez. Her platformun akışı, hata ve belirsiz gönderim sonucu yönetimi ayrıca uygulanacaktır. Hesap bağlama aşamasında gönderi yayımlanmaz. Süresi dolan oturum ve ek doğrulama sahibin tekrar girişini gerektirebilir.

Bulut görüntüsünü yayımlamak süreçlerin veya oturumların başka makinelerde sorunsuz geri geleceğini kanıtlamaz. Girişler yapıldıktan sonra profilin yeni görevde korunması ayrıca test edilmelidir. Giriş içeren snapshot'lara erişim, hesap erişimi gibi korunmalıdır.

## BrowserAct maliyet sınırı

24 Ekim 2026 tarihinde https://www.browseract.com/pricing sayfası kontrol edildi: Free planda 5 yerel tarayıcı ve yerel CLI için sıfır runtime ücreti belirtiliyor. Ücretli bulut botları, fingerprint tarayıcıları ve yönetilen proxy hizmetleri ayrı ürünler. Bu kurulum standart yerel chrome türünü kullanıyor; ücretli tarayıcı/proxy satın alınmadı. Bu bilgi kendi bulut makinemizin barındırma veya ajan kullanım maliyetlerinin sıfır olduğu anlamına gelmez. Fiyatlar ve uzaktan erişimin hesap bazlı kullanılabilirliği değişebilir; ödeme veya ücretli özellik etkinleştirmesi yapmadan önce açık kullanıcı yetkisi gerekir.
