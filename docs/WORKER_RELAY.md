# Mevcut tünele Cloudflare Worker üzerinden bağlantı

PC'den yapılan sağlık, sekme listesi ve Facebook içerik okuma testleri başarılıdır. Facebook sayfa yönetim görünümü doğrulandı; LinkedIn sekmesi yönetici panelindedir. Buna karşın bu Codex ortamı geçici tünel hostname'ine ve `trycloudflare.com` ana adresine aynı metin 403 yanıtını alıyor. Diğer HTTPS sitelerine bağlantı çalışıyor. Bu sonuç, köprü uygulamasını veya hesap girişlerini düzeltmek gerektiğini göstermiyor. Engellemenin kesin sahibi henüz belirlenmedi.

`scripts/cloudflare/bridge-relay.mjs`, sahibinin kendi Cloudflare hesabına yüklenebilen bir Worker modülüdür. DNS taşımadan bir `workers.dev` adresini mevcut tünele bağlamak için hazırlanmıştır. Henüz dağıtılmadı; bu ortamdan Worker'a ve Worker'dan tünele gerçek erişim ayrıca doğrulanmalıdır.

## Kurulum — sahibine adımları tek tek ver

1. Cloudflare panelinde **Workers & Pages → Create application → Create Worker** yoluyla bir Worker oluştur. Arayüz değişirse **Start with Hello World** seçeneği kullanılabilir. Mevcut site/DNS/Nameserver ayarlarını değiştirme; ücretli plan veya ürün açma.
2. Worker'ın **Edit code** ekranında modül içeriğini `scripts/cloudflare/bridge-relay.mjs` ile değiştirip dağıt. Dosyada şifre/token yoktur. Tek upstream, sahibinin doğrulanmış mevcut Quick Tunnel adresidir. Gerçek token kodun içine veya Worker değişkenlerine eklenmez.
3. Gerçek `https://WORKER.HESAP.workers.dev` adresini al. Bu ortamdan anahtarsız `/v1/health` isteğinin Worker'ın JSON 401 yanıtını döndürdüğünü doğrula. 403 devam ederse çözüm tamamlandı deme.
4. Mevcut `WOODMOOD_BRIDGE_TOKEN` secret'ının izinli hedeflerine bu tam Worker hostname'ini ekle; eski binding'i koru. `WOODMOOD_BRIDGE_URL` değerini gerçek Worker origin'iyle güncelle. Taslak kaydının çalışan ortama uygulandığını ayrıca doğrula; gerekirse ürünün kaydet/yayımla adımı gerekir. Token'ı tekrar isteme veya farklı alana sızdırma.
5. Anahtarlı sağlık kontrolünde doğru servis, browser_running ve owner_paused durumunu kontrol et. Sonra sekme listesi ve tek bir içerik okumasıyla uçtan uca erişimi doğrula. Oturum kurulumunda paylaşım yapma.

## Sınırlar

Worker yalnızca sabit upstream'e belirli `/v1/` yollarını ve GET/POST isteklerini aktarır. Authorization ve Idempotency-Key korunur; origin hâlâ gerçek token'ı doğrular. Başka sitelerden gelen tarayıcı Origin istekleri reddedilir. Çerez aktarımı, key logging ve cache yoktur; yönlendirmeler takip edilmez; gövde en fazla 25 MB'dir. Worker kodunu değiştirebilen hesap yöneticilerinin bağlantıya erişimi vardır.

Bu Worker adresi aynı kalabilir, fakat alttaki Quick Tunnel adresi PC yeniden başlayınca değişirse kodun UPSTREAM satırı güncellenmelidir. Bu nedenle PC'nin yeniden başlatılmasında otomatik kalıcı bağlantı talebini tek başına tamamlamaz; Named Tunnel/başlangıç işleri sonraya bırakıldı. Worker kullanımının hesap kotalarını tüketebileceğini dikkate al; ücretli yükseltme satın alma.

Yerel güvenlik/aktarım kontrolleri: `node --test tests/bridge-relay.test.mjs`. Bu testler gerçek Cloudflare dağıtımı veya canlı erişim kanıtı değildir.
