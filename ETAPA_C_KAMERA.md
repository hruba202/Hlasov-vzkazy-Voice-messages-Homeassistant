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
může build adresář vyčistit. Reportové logy etapy B jsou zachované zvlášť.

## Ověření

- Lokální ESPHome 2026.9.0; uživatel na desce ověřil etapu B s ESPHome 2026.9.1.
- `esphome config esp32p4-camera-720p.yaml`: prošlo.
- C++ vygenerováno. Plná kompilace prošla: `Successfully compiled program`.
- Porovnání konfigurací: `investigation/camera-720p/preservation-check.txt`.
- Logy: `investigation/camera-720p/config.log` a `build.log`.
- Vyřešené závislosti jsou v `investigation/camera-720p/dependencies.lock`.
  Verze i hashe všech balíčků odpovídají etapě B (esp_video 2.3.0,
  usb_host_uvc 2.5.2); nebyla přidána ani aktualizována oprava #571.
- V projektu nejsou produkční secrets. Sestavení používá dočasné testovací
  údaje; případná binárka není určena k nasazení.

Dočasné testovací secrets byly po sestavení odstraněny. Výstupní velikosti
a SHA-256 jsou v `investigation/camera-720p/build-artifacts.json`.

| Výsledek | Hodnota |
|---|---|
| OTA binárka | 1 193 632 B |
| Factory binárka | 1 259 168 B |
| Interní DIRAM staticky | 105 666 B / 576 464 B (18,33 %) |
| Statické sekce External RAM | 1 112 668 B |

Shodné statické velikosti s VGA jsou očekávatelné: rozlišení se vybírá za běhu.
Neznamenají shodnou dynamickou spotřebu PSRAM. Procento External RAM ve výpisu
size vychází z adresního prostoru, nikoliv z fyzické kapacity 32 MiB desky.

## Zpětná vazba uživatele 21. 10. 2026

Upřesnění identity od uživatele: celé dosavadní testování a uvedené logy
pocházejí z Jelly Comb (1BCF:28C4, Windows: FHD Camera). Nulaxy
(0C45:636B, Windows: USB 2.0 Camera) byla také samostatně otestována
a funguje bez problémů. Vlastní statistiky fps Nulaxy nebyly dodány;
níže uvedené hodnoty patří Jelly Comb. Úspěšné testy nepatří C270.
Logitech C270 (046D:0825) v logu 06:22–06:24 opakovaně selhává při čekání
na UVC zařízení a host hlásí 0 enumerovaných USB zařízení. To ukazuje problém
před příjmem obrazu; příčina může být v připojení, napájení či enumeraci a
z tohoto výřezu není určena. Není doloženo, že jde o chybu #571.
Hlášení dlouhé operace 500 ms odpovídá čekání na zařízení. Boot je označen
za úspěšný; výřez nedokládá restart nebo pád celého zařízení.

Uživatel v návaznosti na etapu C oznámil, že kamera funguje. Následný log
z 05:12–05:13 potvrzuje skutečně zachycené snímky 1280x720:
- 05:12:50: 9,8 fps, průměr 137 712 B/snímek;
- 05:13:00: 8,1 fps, průměr 146 833 B/snímek.

Běží ESPHome 2026.9.1, kompilované 20. 10. 2026 v 23:51:26, limit 10 fps.
PSRAM je rozpoznaná jako 32768 KB a Ethernet běží 100 Mb/s full duplex.
V tomto výřezu nejsou chyby USB, watchdogu ani upozornění na krátké restarty.
Zařízení hlásí podporu bootloader rollbacku.

Funkční obraz v režimu 720p je tedy potvrzen uživatelem i statistikami.
Dva vzorky nepotvrzují dlouhodobou stabilitu, spotřebu PSRAM ani současný
běh hudby a HuskyLens v 720p. Souběh byl dříve výslovně potvrzen pro VGA.
Automaticky nezvyšujeme limit na 15 fps; stávající limit 10 fps ponecháváme.

Logovací nástroj používá u uživatele název esp32p4-camera.yaml, ale zařízení
prokazatelně posílá 720p. Lokální záloha stejného názvu zůstává 640x480;
lokální varianta 720p je esp32p4-camera-720p.yaml. Ze samotného názvu souboru
proto nelze určovat skutečné rozlišení běžícího zařízení.

## Test na desce a ladění fps

Po úspěšném sestavení a až při uživatelem provedeném nasazení s vlastními
secrets otevřít kameru v HA. Očekávat `Capture resolution: 1280x720 (JPEG)`
a průběžné statistiky `1280x720 @ ... fps, ... B/frame`. Samotný konfigurační
výpis Resolution není důkazem skutečně vyjednaného rozlišení. Pokud komponenta
ohlásí náhradní rozlišení, požadovaný režim 720p není ověřený.

1. Nejprve zaznamenat 2 minuty samotného obrazu, s jediným odběratelem v HA.
2. Pak alespoň 10 minut současného obrazu, hudby a načítání HuskyLens.
3. Vyhodnotit stabilní fps po rozběhu, velikost snímků, plynulost zvuku,
   aktualizace HuskyLens, případné restarty, chyby USB a alokací.
4. Při potížích se vrátit na ověřený `esp32p4-camera.yaml` (640x480).
5. Pokud 720p běží stabilně blízko 10 fps, může následovat samostatný pokus
   s limitem 15. Pokud je dosažené fps výrazně nižší, samotné zvýšení limitu
   nemusí pomoci. Tuto změnu zatím neprovádíme.

max_framerate omezuje předávání snímků do HA, nikoli USB frame interval kamery.
Snížení limitu může snížit kopírování/síťový provoz, ale nemusí odstranit USB
problém. 720p má třikrát více obrazových bodů než VGA; velikost MJPEG snímku
se však mění podle scény a nemusí být přesně trojnásobná.

Skutečná spotřeba PSRAM, CPU, stabilita 720p a fps vyžadují měření na desce.
Úspěšná kompilace tyto vlastnosti nepotvrzuje. Funkčnost jedné kamery nebo
režimu sama nepotvrzuje jiné kamery/režimy ani přítomnost opravy UVC #571.
