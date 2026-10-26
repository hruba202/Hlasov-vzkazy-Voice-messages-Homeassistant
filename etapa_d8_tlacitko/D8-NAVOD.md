# D8 — fyzické tlačítko zvonku

Integrace Dveřní zvonek P4 0.3.0. Připraveno s pomocí OpenAI Codex.

Funkční D7 zůstala zachovaná ve své složce. D8 aktualizuje tutéž integraci v HA a přidává nový ESPHome soubor `esp32p4-doorbell-button.yaml`. Stávající konfigurace, piny audia, HuskyLens, kamera a revize externích komponent se nemění.

## Chování jednoho tlačítka

| Situace | Výsledek stisku |
|---|---|
| Klid, žádný hovor ani záznam | Zazvoní na vybrané panely |
| Vyzvánění nebo aktivní hovor | Nic nemění, nezavěšuje |
| Přehrávání výzvy | Stisk ignoruje, nepamatuje si ho na později |
| Po výzvě: čekání na návštěvníka | Spustí nahrávání P4 |
| Probíhá nahrávání | Ukončí snímání a uloží vzkaz |
| Probíhá odesílání | Stisk ignoruje |

Bez dalšího stisku se snímání samo ukončí po dosavadních 10 sekundách. Čekání po výzvě končí po 60 sekundách bez pořízení nahrávky. Délka záznamu a upload zůstávají ve fungujícím D5 záznamníku.

GPIO vstup filtruje zákmit 30 ms. HA navíc odmítá opakované stisky během jedné sekundy. Dlouhé držení je jeden stisk. Po startu nebo obnovení spojení se reaguje až na skutečný přechod `off → on`, ne na obnovené `on`.

## Nejdřív vyzkoušej logiku bez flashování

1. Ze ZIP aktualizuj jen `/config/custom_components/p4_doorbell` a restartuj HA. Integraci neodebírej.
2. V **Konfigurovat** zachovej D7 entity. Přidej **Vzkaz zastavit a ulozit** a zapni **Po výzvě čekat na stisk zvonku**. Fyzický senzor zatím může zůstat prázdný.
3. Nahraj a vyber vhodnou výzvu, například: „Právě nemůžeme otevřít. Pokud chcete zanechat vzkaz, po skončení této zprávy stiskněte znovu tlačítko zvonku a mluvte. Dalším stiskem vzkaz uložíte. Máte nejvýše deset sekund.“ Použij fungující lokální média, stejně jako v D7.
4. Na stránce **Dveřní zvonek** stiskni **Výzva k zanechání vzkazu**. Po skončení výzvy se má zobrazit čekání; záznam ještě nesmí běžet.
5. Stiskni **Stisk tlačítka zvonku (zkouška)**, promluv do P4, po několika sekundách stiskni znovu. Vzkaz se má uložit kratší než 10 sekund. Nový soubor přehraj v HA.
6. Pro celou návaznost zapni D7 automatiku po nezvednutí, v klidu stiskni zkušební tlačítko a hovor nezvedej. Po timeoutu má zaznít výzva a následovat čekání na další stisk.

Zkušební tlačítko na stránce prochází stejnou logikou jako fyzický kontakt. Původní tlačítko Zazvonit z P4 zůstává přímým vyvoláním hovoru. Režim čekání je při aktualizaci výchozí vypnutý, takže bez změny nastavení zůstane chování D7.

## Zapojení na P4 se zelenými konektory

Pro nový soubor je vybráno **GPIO2**. Ve schématu výrobce je vyvedeno na rozšiřující konektor P6, v současném YAML se nepoužívá a není zaváděcím pinem P4.

- Jeden kontakt obyčejného **beznapěťového spínacího tlačítka** připoj na vývod označený **GPIO2 / IO2**.
- Druhý kontakt připoj na **GND**.
- Zapojení dělej s odpojeným napájením. Nepřipojuj sem 5 V ani vedení napájeného domovního zvonku. Případné podsvícení tlačítka není součástí tohoto dvouvodičového zapojení.
- Orientuj se podle potisku signálů na desce; **GPIO2 není číslo fyzické pozice 2** konektoru. Polohu podle pořadí dutinek z dostupného textu neodhaduji.
- Pro první zkoušku použij krátké vodiče u desky. Dlouhý venkovní kabel vyžaduje samostatně posoudit rušení a ochranu vstupu; zatím se testuje interní pull-up a softwarový filtr.

Podklady: [schéma Waveshare, strana 1, P6 a síť GPIO2](https://files.waveshare.com/wiki/ESP32-P4-WIFI6-POE-ETH/ESP32-P4-WIFI6-POE-ETH-Schematic.pdf), [výrobce: provedení rozšiřujících konektorů](https://docs.waveshare.com/ESP32-P4-WIFI6-POE-ETH), [Espressif: zaváděcí piny GPIO34–38](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32p4/schematic-checklist-esp32p4.html), [ESPHome: GPIO vstup](https://esphome.io/components/binary_sensor/gpio/).

Ověřeno ve zdrojích, nikoli měřením na tvém kusu desky. Potvrdil jsi zelené konektory a dostupné tlačítko; typ kontaktu a skutečné fyzické zapojení zatím na dálku ověřené nejsou. Pokud na konektoru IO2 nevidíš nebo je tlačítko součástí napájeného zvonku, nezapojuj ho podle pořadí pinů a nejdřív upřesni zapojení.

## Nový YAML a vazba v HA

`esp32p4-doorbell-button.yaml` polož vedle stávajících `esp32p4-intercom-vzkazy.yaml`, `esp32p4-intercom.yaml`, `esp32p4-intercom-base.yaml`, složky `components` a vlastního `secrets.yaml`. Soubor obsahuje pouze balíček D5 a jeden GPIO binary sensor. Nemění existující názvy ani ID entit, včetně opraveného ID tlačítka VoIP Call.

V místním projektu chyběl skutečný `secrets.yaml`; ověření proto používá samostatnou kopii s testovacími údaji. **Testovací binárku nepoužívej pro OTA.** Před nasazením musí projít plná kompilace hlavního YAML s tvým skutečným `secrets.yaml`. Podrobnosti výsledku jsou v `OVERENI.md`. Nic nebylo flashováno.

Po tebou schváleném nasazení firmwaru v HA přibude **Zvonek fyzicke tlacitko**. V nastavení Dveřního zvonku ho vyber jako fyzický senzor. Není potřeba přidávat automatizaci ani povolovat ESPHome volání akcí HA: integrace sleduje změnu jeho stavu přes již používané připojení ESPHome.

Očekávaný log při stisku: změna binary sensoru `Zvonek fyzicke tlacitko` na ON, při uvolnění OFF. Při následném záznamu očekávej existující zprávy D5 `Nahravam, nejvyse 10 s`, `Odesilam do HA`, `Ulozeno v HA`. Pokud HA není dostupný, stisk se neukládá k pozdějšímu opakování a hovor se nezahájí. Již spuštěný desetisekundový záznam dál řídí P4.

## Kontroly a návrat

Otestuj krátký stisk, dlouhé držení, stisk při hovoru, čekání bez stisku, uložení kratší zprávy a automatické ukončení po 10 s. Ověř, že přijmutý hovor nevytvoří následně vzkaz. Po restartu HA s drženým tlačítkem se nemá samo zazvonit; tlačítko uvolni a znovu stiskni.

Pro návrat na D7 vypni režim čekání a odeber volbu fyzického senzoru, případně vrať integrační balíček 0.2.0 a restartuj HA. Nový GPIO senzor ve firmwaru sám žádné hovory ani záznamy nevyvolává.

Režim nepřítomnosti, snímky po detekci HuskyLens a automatické odemykání se v této etapě nemění.
