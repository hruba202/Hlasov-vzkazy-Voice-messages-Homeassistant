# HomeKey společně s audiem a HuskyLens na ESP32-P4

Stav průzkumu: 20. 10. 2026. Uživatel už má fungující samostatné ESP32
s HomeKey přes MQTT; tuto sestavu není nutné pořizovat ani znovu vytvářet.

## Závěr z kontroly zdrojů

Nenašel jsem konflikt hardwarových pinů, který by jednu desku vylučoval.
Překážkou je přenos a údržba softwaru. Není to jen změna YAML či jedné hlavičky:
zasahuje se do HAP-ESPHome, jeho HomeKit SDK a NFC ovladače.
Jde podle mého posouzení o středně velký port s nutnými zkouškami na zařízení.
Nejde o prokázanou nemožnost HomeKey na P4.

Protože oddělené ESP32 už funguje, doporučuji je pro běžný provoz zachovat.
Varianta jedné desky dává smysl jako samostatný vývojový pokus, pokud má sjednocení
hardwaru větší hodnotu než jednoduché aktualizace a oddělení poruch.
Plán zatím automaticky neměním.

## Co by skutečně bylo nutné upravit

| Oblast | Nález | Nutná práce |
|---|---|---|
| Podpora P4 | MFi I2C soubor v SDK nemá větev pro P4 a vyvolá preprocesorovou chybu. | Pro běžný ne-MFi režim jej nezahrnovat do sestavení; případně zvlášť portovat, pokud by byl požadován MFi hardware. |
| Ethernet | HAP-ESPHome volí Wi-Fi transport. SDK navíc volá přímo Wi-Fi API při kontrole konfigurace, získávání MAC, resetu a testovacím reconnectu. | Zvolit Ethernet, přizpůsobit získání identity a oddělit nepotřebné Wi-Fi větve. Prověřit všechny odkazované symboly při linkování. |
| NFC čekání | `inDataExchange()` až 251krát zavolá `read_ready_(true)`, kde každé volání může čekat přes 100 ms. | Nahradit počítání pokusů jedním časovým limitem; pro spolehlivý souběh posoudit i neblokující průběh celé autentizace. |
| Krátká NFC odpověď | Test `versions.size() > 0` předchází přístupu na `size()-2`. Jednobajtová odpověď může způsobit přístup mimo rozsah. | Ověřit minimálně stavový byte a dva stavové byty odpovědi před indexováním. |
| Souběh | HomeKey autentizace se spouští synchronně z NFC callbacku. | Změřit dobu blokování hlavní smyčky, chování watchdogu, aktualizace HuskyLens a zvuk při úspěšné i přerušené autentizaci. |
| Údržba | Opravy zasahují do více upstream komponent. | Používat konkrétní revize závislostí a udržovat patche při aktualizaci ESPHome. |

Přibližně 25 sekund u NFC je **odvozená krajní doba čekání podle zdrojů**,
nikoli naměřená běžná doba odemknutí. `yield()` v čekání může pustit jiné RTOS úlohy,
ale nezaručí návrat do hlavní komponentové smyčky ESPHome. Nelze tedy automaticky
tvrdit, že se vždy zastaví zvuk; zastavení pravidelné obsluhy hlavní smyčky je však
pro tuto společnou sestavu relevantní problém.

Připravený návrh opravy omezuje fázi čekání na připravenou odpověď na 250 ms;
nejde o limit celé výměny včetně odeslání a potvrzení příkazu. Ani to
není plně neblokující autentizace: HomeKey může provést více výměn za sebou.
Zvolené časování je nutné ověřit se skutečnou PN532 a telefonem.

## Upřesnění síťové závislosti

Ve staženém ESP-IDF 5.5.5 komponenta `esp_wifi` při vypnutém lokálním/hostovaném
Wi-Fi poskytuje hlavičky a vazby na netif. Není to důkaz, že poskytuje kompletní
implementaci API, kterou volá starší HomeKit SDK. Samotná existence hlavičky
`esp_wifi.h` tedy nestačí. Rozsah dosažitelných Wi-Fi volání a případné chyby
linkování musí uzavřít plné sestavení.

Použití C6 jako ESP-Hosted je jiná možná cesta k Wi-Fi API, ale přidalo by další
závislost na firmwaru koprocesoru a jeho inicializaci. Neřeší samo o sobě NFC
čekání ani nesprávný výběr HomeKit transportu.

## Připravené podklady

- `investigation/hap-prototype.patch`: přepnutí transportu podle `USE_ETHERNET`,
  vynechání Wi-Fi služby na Ethernetu, celkový limit NFC čekání a kontrola délky
  odpovědi.
- `investigation/sdk-mfi-prototype.patch`: nezařazovat MFi I2C soubor, pokud
  `CONFIG_HAP_MFI_ENABLE` není zapnuté.

Oba patche prošly `git apply --check` proti referenčním commitům z `ETAPA3.md`.
To potvrzuje pouze jejich použitelnost na dané zdroje, **ne kompilaci nebo funkci**.
Patche zatím nejsou aplikované ani zapojené do hlavního YAML a neřeší celou
síťovou část. Kryptografická implementace HomeKey se nepřepisovala.

Pokus o úplné sestavení nedošel ke kompilaci projektových zdrojů. Po stažení
ESP-IDF 5.5.5 skončila příprava prostředí chybou chybějících nástrojů
`xtensa-esp-elf` a `dfu-util` (viz `homekey-build.log`). To není důkaz chyby
projektového kódu ani úspěšného sestavení. Výše uvedené nálezy jsou výsledkem
kontroly zdrojů; možné chyby linkování a chování na zařízení zůstávají neověřené.

Dosavadní `esp32p4.yaml`, návrh `esp32p4-homekey.yaml` i reference zůstávají
beze změny funkčního chování.

## Podmínky, za kterých má cenu pokračovat s jednou deskou

1. Sestavení bez falešných náhrad kryptografie či Wi-Fi API, které by jen
   skryly skutečný problém.
2. Párování a obnovení spojení HomeKit po odpojení/připojení Ethernetu.
3. HomeKey s oprávněným telefonem, odmítnutí neplatného přístupu, přerušení
   komunikace odebráním telefonu a následný nový pokus.
4. Zachování párování po restartu a OTA.
5. Přehrávání a HuskyLens současně s NFC; BLE přidat až po tomto ověření.

Pokud by bylo nutné výrazně přepisovat autentizační knihovnu nebo předělávat
celý NFC průběh do jiné úlohy, doporučuji pokus ukončit a využít už funkční
samostatné ESP32. Přesun do vlastní úlohy vyžaduje také bezpečné předávání stavů
do ESPHome; není to pouhé přidání `xTaskCreate`.

## Doložení nálezů

- [Wi-Fi transport v HAP-ESPHome](https://github.com/rednblkx/HAP-ESPHome/blob/0ab12c97f33d894909a35b24b9e837384d063861/components/homekit_base/HAPRootComponent.cpp)
- [Čekání v PN532 – inDataExchange a read_ready_](https://github.com/rednblkx/HAP-ESPHome/blob/0ab12c97f33d894909a35b24b9e837384d063861/components/pn532/pn532.cpp)
- [HomeKey callback a kontrola versions](https://github.com/rednblkx/HAP-ESPHome/blob/0ab12c97f33d894909a35b24b9e837384d063861/components/homekit/lock.cpp)
- [Wi-Fi větve SDK](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_core/src/esp_hap_wifi.c)
- [MAC identita v SDK](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_core/src/esp_hap_acc.c)
- [Zařazení MFi I2C do sestavení](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_platform/CMakeLists.txt)
