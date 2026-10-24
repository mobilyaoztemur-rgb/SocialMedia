# Windows bilgisayarı kalıcı tarayıcı olarak hazırlama

Bu sürüm Windows 10/11 için hazırlanmıştır. Python API'si, gerçek Chromium işlemleri ve profil kalıcılığı mevcut Linux bulut makinesinde test edildi. Windows `.cmd` dosyaları ve isteğe bağlı Görev Zamanlayıcı kaydı bu makinede çalıştırılmadı. Cloudflare üzerinden gerçek PC erişimi ve sosyal hesap girişleri de henüz doğrulanmadı.

## Kurulacak düzen

- Windows'ta görünür, ayrı bir Chrome penceresi; mevcut kişisel Chrome profilinden bağımsız.
- Kalıcı profil ve erişim anahtarı `%LOCALAPPDATA%\WoodmoodSocial` içinde, Git dışında.
- Sadece loopback'e bağlı kontrol servisi, 8787 portu. Tüm API yolları rastgele üretilmiş uzun bir Bearer anahtarı ister. Şema, CDP veya çerez dışarı aktarma uç noktası yoktur.
- İlk test için alan adı ve Cloudflare hesabı gerektirmeyen Quick Tunnel. Adres rastgeledir ve yeniden başlatmada değişebilir.
- Bulut görevinden HTTPS kontrol istemcisi; BrowserAct'a ve onun 9070 portlu geçidine ihtiyaç duymaz.

## 1. Bilgisayardaki önkoşullar

Normal Windows kullanıcı hesabında çalıştırın. Chrome penceresi masaüstünde açılır; SYSTEM/arka plan servis hesabı kullanmayın.

Google Chrome ve `uv` kurulu olmalı. Terminalde eksik olanı yükleyebilirsiniz:

```powershell
winget install --id Google.Chrome --exact
winget install --id astral-sh.uv --exact
winget install --id Cloudflare.cloudflared --exact
```

Bunlar kurulum önerileridir; bu sohbet bilgisayarınızda bu komutları henüz çalıştırmadı. Kurulumdan sonra yeni terminal açın. Python 3.12 ve kilitli paketleri uv hazırlar. Güvenlik/sertifika doğrulamasını kapatmayın.

## 2. Kodları açma ve kurulum

Kaynak kod veya `woodmood-pc-setup.zip` paketini sabit bir klasöre açın. Paket, `scripts/package-pc.py` ile sadece izin verilen kaynak dosyalarından üretilir; tarayıcı profili, parola, token, veritabanı ve `.env` içermez. Paketin SHA-256 dosyası birlikte üretilir.

Terminalden veya dosyaya çift tıklayarak:

```text
scripts\pc\setup.cmd
scripts\pc\owner-browser.cmd
```

Birinci dosya kurar ve özel anahtarı ilk seferde üretir. Tekrar çalıştırmak eski anahtarı, profili veya sahibin ayarlarını değiştirmez. İkinci dosya aynı Woodmood profiliyle **normal Chrome** açar: otomasyon sürücüsü ve uzaktan hata ayıklama bağlantısı yoktur. Mevcut kontrol servisi çalışıyorsa önce onun terminalinde Ctrl+C ile durdurmanız istenir. Profil ve anahtar değiştirilmez.

Varsayılan özel dosyalar:

```text
%LOCALAPPDATA%\WoodmoodSocial\bridge.json
%LOCALAPPDATA%\WoodmoodSocial\bridge-token
%LOCALAPPDATA%\WoodmoodSocial\chrome-profile\
%LOCALAPPDATA%\WoodmoodSocial\owner-control
```

Bu klasörü genel paylaşıma, Git'e veya herkese açık bir yedeğe koymayın. Windows kullanıcı hesabınızın ACL izinleriyle korunur; paylaşımlı Windows hesabı kullanmayın. Yerel profil aynı Windows kullanıcısına bağlıdır; başka makineye klasörü kopyalamak girişlerin çalışacağını garanti etmez.

## 3. Hesaplara sizin giriş yapmanız

İlk kurulumda **sahip modu** aktiftir. Google gibi sağlayıcıların otomasyonla açılan girişleri engelleyebilmesi nedeniyle ilk giriş, kontrol servisi tamamen kapalıyken `owner-browser.cmd` ile açılan normal Chrome içinde yapılır. Kontrol servisi daha sonra aynı profile bağlanır. Servis çalışırken de sahip modu sayfa listesini, ekran görüntüsünü, metin okumayı ve tıklamayı 423 ile engeller. Bu dosya modu tek başına tarayıcıdaki otomasyon bağlantısını kaldırmaz; giriş için normal pencereyi kullanın.

Yeni açılan Chrome penceresinde sırayla hesaplara girin. Facebook için sayfayı yönetebilen kişisel hesabınızla giriş yapın, sonra Woodmood sayfasını açın. MFA/doğrulamaları kendiniz tamamlayın. Şifreleri sohbete girmeniz gerekmez; isterseniz daha sonraki otomasyon gereksinimleri için uygun secrets deposunda ayrıca saklanabilirler.

1. https://www.facebook.com/mobilyawoodmood
2. https://www.instagram.com/mobilyawoodmood/
3. https://www.linkedin.com/company/mobilyawoodmood
4. https://tr.pinterest.com/mobilyawoodmood/
5. https://www.threads.com/@mobilyawoodmood
6. https://www.tumblr.com/mobilyawoodmood
7. https://x.com/mobilyawoodmood
8. https://www.youtube.com/@mobilyawoodmood
9. https://www.tiktok.com/@mobilyawoodmood

Sırasıyla ilerlemek için önce yalnızca Facebook'a da giriş yapabilirsiniz. Hesapların her birinde doğru profil ve yönetici erişimi daha sonra ayrıca doğrulanacak.

Girişler bitince **bu Chrome penceresini tamamen kapatın**, sonra çalıştırın:

```text
scripts\pc\start-bridge.cmd
scripts\pc\agent-ready.cmd
```

Bu, sahibin tarayıcıyı ajana devretmesidir; sosyal hesaba gerçekten giriş yapılmış olduğu iddiası değildir. Tekrar siz kullanacaksanız önce:

```text
scripts\pc\owner-login.cmd
```

Bu dosya yeni ajan işlemlerini engeller ve devam eden işlemin bitmesini bekler. Normal bir giriş penceresine geçmek için bundan sonra `start-bridge.cmd` terminalinde Ctrl+C ile servisi durdurun, `owner-browser.cmd` çalıştırın. Girişten sonra Chrome'u kapatın, servisi yeniden başlatın ve `agent-ready.cmd` ile devredin. Aynı profilde iki farklı Chrome sürecini zorla açmayın.

## 4. Alan adı olmadan ilk Cloudflare bağlantısı

Ayrı terminalde çalıştırın:

```text
scripts\pc\start-tunnel.cmd
```

Cloudflared ekranda `https://…trycloudflare.com` biçiminde bir adres verecek. Bu adresi sohbete iletebilirsiniz. IP/port yönlendirme, BrowserAct anahtarı veya Cloudflare yönetici token'ı gerekmez.

Quick Tunnel **geçici test erişimidir**: yeniden başlatmada adres değişir, servis kalıcılığı veya SLA sağlamaz. İstek/SSE gibi ürün sınırları vardır; bizim istemci normal HTTPS/JSON kullanır. Bu denemede Cloudflare Access SSO kurulmuş değildir; HTTPS ve tüm origin yollarında uzun Bearer anahtarı ile korunur. Tarayıcı debug portu internete açılmaz.

Makinenin Cloudflare tünel sunucularına çıkış erişimi gerekir. `--protocol http2` QUIC yerine TCP taşımayı seçer; bu, her ağda çalışacağı garantisi değildir. Bir tünel hatasında doğrulanmış ağ teşhisinden önce yeni abonelik alınmaz.

Sabit adres için daha sonra Cloudflare'da yönetilen bir alan adı ve named tunnel seçebiliriz; bu aşamada Access ile sahip ve servis erişimleri de ayrılabilir. Mevcut `woodmoodmobilya.com` alan adının yönetimi elinizdeyse yeni alan adı almak zorunlu olmayabilir; DNS taşıma/değişiklikleri ayrı değerlendirilir.

## 5. Sohbet ortamına bağlantıyı tanıtma

Kontrol istemcisi şu alanları okur:

| Alan | Açıklama |
|---|---|
| `WOODMOOD_BRIDGE_URL` | Tünelin HTTPS adresi; gizli değildir |
| `WOODMOOD_BRIDGE_TOKEN` | PC'de üretilen `bridge-token` dosyasının içeriği |
| `CF_ACCESS_CLIENT_ID` ve `CF_ACCESS_CLIENT_SECRET` | Yalnızca ileride Cloudflare Access servis koruması kurulursa |

Anahtar tek başına PC'nin dosyalarını veya kabuk komutlarını açmaz; sadece bu profilin sınırlı tarayıcı API'sini yetkilendirir. Tarayıcı hesabına erişim sağladığı için gizli tutulur. Değeri komut satırı argümanına veya repoya yazmayın.

Windows'ta anahtarı terminale yazdırmadan panoya almak için:

```powershell
Get-Content "$env:LOCALAPPDATA\WoodmoodSocial\bridge-token" -Raw | Set-Clipboard
```

Ardından güvenli ortam secret alanına yapıştırılabilir. GitHub Secrets da kullanılabilir, fakat bu sohbet onları normal repo okumasıyla alamaz; ilgili workflow'un çalışma ortamına aktarması gerekir. Gerçek tünel adresi belli olunca bu Codex ortamına uygun secret bağını ve hedef alan adını tanımlarız. Token değerini URL içine eklemeyin.

Alternatif, kontrol istemcisini özel yerel ayar dosyasıyla hazırlamaktır. Aşağıdaki örnek adresi gerçek adresle değiştirin; anahtar `getpass` ile görünmeden istenir:

```bash
uv run --frozen python -m woodmood.remote configure --url https://GERCEK-ADRES.trycloudflare.com
uv run --frozen python -m woodmood.remote health
uv run --frozen python -m woodmood.remote pages
```

Henüz gerçek PC adresi olmadığı için bu bağlantı bu sohbetten tamamlanmış değildir. Bir MCP yapılandırmasını dosyaya yazmak yerine mevcut terminal aracı HTTPS istemcisini çağırır. Bu, şu anki sohbet araçlarıyla uyumludur; yeni sohbetlerin de aynı kaynaklara ve yetkilendirmeye erişmesi gerekir.

## 6. Bağlantı kabul kontrolü

1. Anahtarsız istek 401 ile reddedilmeli. Yetkili `/v1/health` servisin adını ve tarayıcı durumunu göstermeli.
2. Sahip modu açıkken sayfa okumaları ve işlemler 423 ile durmalı.
3. Sahip hazır dediğinde yalnızca doğru sosyal sayfa ve yönetim erişimi okunarak doğrulanmalı; kurulumda gönderi paylaşılmamalı.
4. Tarayıcı ve servis kapatılıp tekrar açılmalı; oturumun ve aynı hesabın korunduğu kontrol edilmeli.
5. Bu bulut ortamından ve sonraki yeni görevde aynı erişim tekrar denenmeli.

Geliştirme testleri gerçek Chromium üzerinde sentetik bir sayfa kullanır. Bunlar Facebook/Instagram/LinkedIn girişinin veya bütün yayın akışlarının test edildiği anlamına gelmez. Oturumun platform tarafından sonlandırılması, CAPTCHA ve MFA durumlarında sahibin tekrar giriş yapması gerekebilir.

## 7. Kalıcı çalışma ve Windows başlangıcı

Bilgisayarın uyku/hibernasyon ve ağ kesintisi davranışlarını ihtiyaca göre ayarlayın; servisler ancak makine açıkken erişilebilir. Windows yeniden başlaması ve Chrome güncellemelerinden sonra erişim tekrar kontrol edilir.

İsteğe bağlı `scripts/pc/register-startup.ps1`, kontrol servisini bu kullanıcının **Windows'a girişinde**, masaüstünde başlatan sınırlı yetkili bir Görev Zamanlayıcı kaydı hazırlar. Mevcut aynı adlı görevin üzerine yazmaz. Bu script Linux ortamında çalıştırılmadı; PC'de incelenip test edilmelidir. Bir Windows hesabı giriş yapmadan görünür Chrome oturumu çalıştırmayı vaat etmez. Quick Tunnel, adres değişikliği nedeniyle ayrı başlatılır.

## Yayın kapsamı

Kontrol servisi platform başına tarayıcı akışlarını kullanmaya temel sağlar: sayfa açma, güncel DOM okuma, ekran görüntüsü, tıklama, metin doldurma ve medya seçme. Cookie dışa aktarma, rastgele JavaScript ve shell komutu uç noktası yoktur. Bir işlem anahtarının tekrarı aynı tarayıcı eylemini yeniden yürütmez; sonucu belirsiz eylemde önce sayfa kontrol edilir. Bu, her sosyal platformda tam bir kez yayın garantisi değildir.

Kullanıcının proje kuyruğu Azerbaycan → Fırat Serhat Motors → Mormenekşe → Northernland, sonra yeni keşiflerdir. Paylaşım sıklığı hâlâ belirlenmedi; otomatik yayın worker'ı açılmadı. Hesaplar bağlandıktan sonra her platformun yükleme/yayınlama adımı ve gerçek gönderi bağlantısı doğrulanacaktır.

## İsteğe bağlı GitHub bağlantı kontrolü

Kodlar GitHub'a gönderildikten sonra `.github/workflows/remote-status.yml`, yalnızca elle çalıştırılan **Check PC connection** işini sağlar. Repo değişkeni `WOODMOOD_BRIDGE_URL` ve repo secret'ı `WOODMOOD_BRIDGE_TOKEN` ayarlanır. Cloudflare Access ayrıca kurulmadıysa CF_ACCESS alanları boş bırakılır. Workflow, bu değerleri çalışma ortamına aktarır ve yalnızca servis sağlık bilgisini kontrol eder; Chrome ekranını, hesap içeriğini veya anahtarları loglara yazmaz. Sosyal ağa gönderi göndermez.

Workflow dosyaları hazırlandı, ancak bu çalışma sırasında GitHub'a push yapılmadı veya bir GitHub workflow'u çalıştırılmadı. Geçici tünel adresi değişirse repo değişkeni ve bu sohbetin istemci adresi güncellenmelidir. GitHub Actions erişimi, benim bu sohbetten PC'ye erişimimin ayrıca doğrulanması gereğini ortadan kaldırmaz.

## Google “Bu tarayıcı veya uygulama güvenli olmayabilir” uyarısı

Google, desteklenen Chrome kullanılsa bile otomasyonla kontrol edilen tarayıcıdan girişi engelleyebilir. Chromium'un açık kaynaklı olması bu giriş politikasını değiştirmez. Bu nedenle normal manuel giriş ile otomasyon bağlantısı bu sürümde ayrıldı. Güvenlik kontrolleri kapatılmaz, user-agent/kimlik gizleme veya CAPTCHA atlatma yöntemi uygulanmaz.

Güncelleme için eski servisi durdurun ve yeni ZIP'i ayrı bir klasöre açın. `owner-browser.cmd` mevcut LocalAppData profilini kullanır; eski oturumları veya anahtarı silmez. Google girişini bu pencerede kendiniz tamamlayın. Uyarı burada da sürerse bu yöntem için başarı iddiasında bulunmayız; Google'ın desteklenen tarayıcı/hesap doğrulama adımlarını izler veya o platform için resmî OAuth/API bağlantısını değerlendiririz.

Kaynaklar: https://support.google.com/accounts/answer/7675428?hl=tr ve https://developer.chrome.com/blog/remote-debugging-port .

## owner-browser çalışırken ConnectTimeout hatası

Windows'ta eski sürümün `owner-browser.cmd` yolu, servis kapalı mı diye HTTP sağlık isteği yaparken `httpx.ConnectTimeout` verebiliyordu. Düzeltilmiş sürüm manuel giriş için HTTP isteği yapmaz; yerel portun boşluğunu kontrol eder. Port dolu veya sistem tarafından ayrılmışsa güvenli biçimde durur ve açıklayıcı mesaj verir. Sağlık yanıtı gelmemesi servisin kapalı olduğu kabul edilmez.

Bu hatada Starlette veya başka paketleri tek tek kurmak gerekmez. `starlette==1.9.0` gibi satırlar kurulum çıktısıdır; PowerShell komutu değildir. Yeni ZIP'i ayrı klasöre açın; eski servisi Ctrl+C ile durdurup yeni `scripts\pc\owner-browser.cmd` dosyasını çalıştırın. Mevcut LocalAppData profili ve anahtarı korunur. `owner-login.cmd` sağlık isteği zaman aşımında da artık traceback yerine açıklayıcı mesaj verip sahip modunu korur.

## Sabit adres ve yeniden başlatma

Kullanıcı sabit adres istedi. Named Tunnel için konfigürasyon üretimi, `start-stable-tunnel.cmd` ve isteğe bağlı `register-stable-startup.ps1` hazırlandı. Bunlar Cloudflare hesabı/aktif zone/gerçek tünel UUID ve credential dosyası oluşturulmadan çalışır bağlantı sağlamaz. Aşamaları ajanla **tek tek** uygulayın; [STABLE_ADDRESS.md](STABLE_ADDRESS.md). Mevcut geçici bağlantıyı yeni sabit adres doğrulanmadan kapatmak gerekmez. Bilgisayarın kapalı olduğu sürede adres aynı kalır ancak servis çevrimdışı olur; görünür Chrome için Windows kullanıcısının giriş yapması gerekir.
