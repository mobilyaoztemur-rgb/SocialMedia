# Sabit PC erişim adresi

Kullanıcı, Windows yeniden başladığında adresin değişmemesini istedi. Quick Tunnel deneme adresi kalıcı değildir. Önerilen hedef **kontrol.woodmoodmobilya.com** gibi bir alt alan adıyla Cloudflare Named Tunnel'dır. Bu belge bir hazırlık planıdır; henüz Cloudflare veya DNS değişikliği yapılmadı.

## Mevcut doğrulanmış durum

- Sahibi, geçici adrese kendi PC'sinden anahtarla bağlanıp `woodmood-pc-bridge`, `browser_running=true`, `owner_paused=false`, `busy=false` yanıtını aldı. Yerel Chrome/servis ve PC üzerinden tünel çalışıyor.
- Bu Codex bulut ortamının aynı adrese anahtarlı/anahtarsız istekleri hâlâ 403 `Your request was blocked.` alıyor. Kaynak belirlenmedi; kalıcı alan adının bunu kesin çözeceği söylenemez. Yeni adres bu ortamdan ayrıca test edilecek.
- Google DNS sorgusunda woodmoodmobilya.com için NS kayıtları `dns10.ovh.ca` ve `ns10.ovh.ca`, A kaydı `151.80.155.102` döndü. Önerilen kontrol alt alan adı bulunmadı. Bu kayıtlar yalnızca okunmuştur; alan adı hesabına erişim veya yazma yetkisi kanıtlanmış değildir.
- Kullanıcıya OVH/DNS yönetim erişimi soruldu. Kullanıcı komutları **tek tek** almak istiyor; tüm dağıtım komutlarını aynı anda göndermeyin.

## Uygulanacak aşamalar

1. DNS/alan adı yönetim erişimini netleştir. Standart Named Tunnel özel hostname akışı için Cloudflare'da aktif yönetilen zone gerekir. Mevcut DNS'in taşınması gerekirse A/AAAA/CNAME/MX/TXT ve posta/site kayıtları önce eksiksiz envanterlenmeli, somut değişiklikler değerlendirilmelidir. Sadece yeni alt alan adı isteniyor diye bütün sitenin nameserver'larını otomatik değiştirme.
2. Kullanıcının Cloudflare hesabıyla PC'de tunnel login ve named tunnel oluştur. Bu, ücretli plan veya alan adı satın alma yetkisi değildir. `cert.pem` ve tunnel credentials JSON'u repo dışında kalır.
3. Gerçek UUID ve credential dosyasıyla `python -m woodmood.bridge named-tunnel --id GERCEK_UUID --hostname GERCEK_HOSTNAME` yerel özel konfigürasyonu oluşturur. `--credentials` isteğe bağlıdır; varsayılan dosya Windows kullanıcısının `.cloudflared` dizinidir. Hostname yönlendirmesi/DNS bu komutla oluşturulmaz.
4. `scripts/pc/start-stable-tunnel.cmd`, LocalAppData/WoodmoodSocial/tunnel.yml üzerinden aynı named tunnel'ı çalıştırır. Dosya yoksa durur. JSON içeriği YAML olarak geçerlidir. Özel konfigürasyon mevcutsa farklı ayarlarla üzerine yazılmaz.
5. Yeni adreste anahtarsız 401, anahtarlı doğru sağlık sonucu ve sahip modu kontrolü yapılmalı; bu bulut ortamından erişim doğrulanmalı. Geçici tüneli ancak yeni bağlantı doğrulandıktan sonra kapat.
6. Aynı bridge token'ını yeniden kullan. Ortamın secret hedef alan adına yeni hostname'i doğru kapsamda ekle ve URL değerini güncelle; ikinci bir PC anahtarı isteme. Cloudflare Access koruması eklenecekse insan ve servis erişimleri ayrı yapılandırılır.
7. Manuel başlangıç başarılı olduktan sonra `register-stable-startup.ps1`, köprü ve kalıcı tüneli mevcut kullanıcının Windows'a girişinde başlatacak iki görevi hazırlar. Mevcut görevlerin üzerine yazılmaz. Görünür Chrome için kullanıcı masaüstü oturumu gerekir; Windows login olmadan erişim vaadi verilmez.
8. Yeniden başlatma testinde hostname'in aynı kaldığını, doğru PC'ye ulaşıldığını ve oturumun korunduğunu doğrula. PC kapalı veya ağdan kopukken sabit URL erişilebilir bir makine oluşturmaz; bağlantı çevrimdışı olur.

## Hazırlık ve doğrulama sınırları

Named tunnel config üretimi ve doğrulama testleri yerelde çalıştırılabilir. Windows Görev Zamanlayıcı scripti bu Linux ortamında çalıştırılamaz; gerçek DNS, Cloudflare login/tunnel/route ve reboot testi kullanıcı PC'sini bekler. Gerçek tunnel secret'ları hiçbir örneğe veya kaynak ZIP'e eklenmez. Bu aşamada kullanılabilecek kalıcı hostname hazırlanmış olsa da henüz yayında değildir.
