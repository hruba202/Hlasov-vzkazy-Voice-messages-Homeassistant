# Etapa C – USB kamera v rozlišení 1280x720

Sestavení: 20. 10. 2026. Report aktualizován 21. 10. 2026. Agent neflashoval.

## Konfigurace a změny

Nový soubor `esp32p4-camera-720p.yaml` přebírá celou etapu B přes packages.
Porovnání sloučených konfigurací potvrdilo jedinou změnu: resolution 1280x720
místo 640x480. Zůstává MJPEG, max_framerate 10, usb_peripheral_map 0x01,
ESP-IDF 5.5.5 a commit komponenty 53a315e76c69178d913e6744314408a98bc87234.
HuskyLens, media_player, síť, secrets, kompatibilita logování i ostatní volby
zůstávají zachované. Bez usb_host, HomeKey a BLE proxy.

Soubor `esp32p4-camera.yaml` zůstává funkční zálohou 640x480; nemění se ani
`esp32p4.yaml`. Varianta 720p používá tentýž build adresář, takže výstupní
binárky patří vždy poslednímu sestavení. ESPHome při přechodu konfigurací
může build adresář vyčistit. 
