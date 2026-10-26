# Ověření D8 / 0.3.0

- ESPHome 2026.10.0, ESP-IDF 5.5.5.
- `esphome config`: prošlo.
- Generování C++: prošlo, GPIO2, input + pull-up, inverted, filtr 30 ms.
- Plná kompilace: **prošla**, `INFO Successfully compiled program`.
- 37 lokálních testů integrace se simulovaným HA: prošlo.
- Syntaxe Python, JavaScript, JSON: prošla.
- Skutečná zkouška D8 v HA a na GPIO tlačítku: **dosud neprovedena**.

## Paměť testovací sestavy

- Velikost OTA binárky: **1 456 832 B**.
- Statická RAM dle sestavení: **109 994 / 576 464 B (19,1 %)**.
- Flash dle sestavení: **1 456 428 / 16 515 072 B (8,8 %)**.
- Volná PSRAM a dynamická RAM za běhu se z kompilace neověří; nebyl proveden nový běh na desce.

## Závislosti

Skutečně vyřešené verze z dependencies.lock, stejné jako v předchozí místní sestavě D5:

- `espressif/esp_video`: `2.3.0`
- `espressif/usb_host_uvc`: `2.5.2`
- `espressif/usb_host_uac`: `1.5.0`
- `espressif/esp_codec_dev`: `2.0.0-beta5`
- `idf`: `5.5.5`

Připnutí externích ESPHome komponent se neměnilo. Kompilátor vydal varování `ESPHOME_LOG_TAG redefined` z dosavadní vrstvy kompatibility kamery; sestavení dokončil bez chyby.

## Oddělené testovací údaje

V kořeni projektu není skutečný secrets.yaml. Validace a kompilace proto proběhly v `.validation-d8` s výslovně testovacími hodnotami. Tyto údaje ani testovací binárky nejsou v distribučním ZIP. **Pro nasazení zkompiluj hlavní YAML s vlastními skutečnými secrets. Testovací binárku neflashuj.**

Do HA nebylo nic nasazeno, deska nebyla flashována a původní D4–D7 soubory se neměnily. Nový firmware přidává jeden binary sensor. Předchozí funkční firmware a D7 integrační balíček zůstávají k dispozici.

Plný pracovní log je lokálně v validation-compile.log, není součástí ZIP. Testovací skripty jsou pro kontrolu kódu; pro běžnou zkoušku není potřeba spouštět Python ani vytvářet virtuální prostředí. Použij tlačítka v HA podle D8-NAVOD.md.
