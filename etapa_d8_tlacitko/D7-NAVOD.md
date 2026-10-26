# D7 — výzva, záznam P4 a uložení do HA

Verze 0.2.0, 26. 10. 2026. Vytvořeno s pomocí OpenAI Codex.

Toto je aktualizace integrace **Dveřní zvonek P4**, nikoli druhá souběžná integrace. Firmware P4, fungující VoIP a Hlasové vzkazy se nemění. Nové soubory vznikly v samostatné složce `etapa_d7_vzkaz`; původní D6 zůstala zachovaná.

## Co přibylo

- Tlačítko **Výzva a nahrát vzkaz 10 s** na stránce zvonku. Přehrává na P4 a nahrává její mikrofon, nikoli mikrofon PC.
- Tlačítko **Zrušit sekvenci vzkazu**, použitelné také ke zrušení čekání na nezvednutý hovor.
- **Konfigurovat** v nastavení integrace: výběr zvukové výzvy a existujících entit záznamníku. Nic se nemusí psát do YAML.
- Volitelná automatika po potvrzeném nezvednutí hovoru. Výchozí je **vypnutá**.
- Zobrazení stavu záznamníku P4. Uložení je potvrzeno až novou zprávou `Ulozeno v HA`, kterou firmware vydává po HTTP 201.

Dosavadní tlačítko přednastavené odpovědi zůstává samostatné: převezme hovor, zavěsí a přehraje odpověď. Samo nahrávání nespouští. Pro D7 se vybírá zvláštní výzva před záznamem.

## Aktualizace

1. Ze ZIP `D7-zvonek-vzkazy-0.2.0.zip` nahraď pouze složku `/config/custom_components/p4_doorbell`.
2. Restartuj HA a znovu načti stránku Dveřní zvonek. **Integraci neodebírej**: výběr panelů a zvonková skupina zůstanou zachované.
3. V **Nastavení → Zařízení a služby → Dveřní zvonek P4 → Konfigurovat** nastav vzkazy podle tabulky níže. Pokud frontend změnu ještě neukazuje, obnov stránku prohlížeče.

| Pole | Co vybrat ze stávající P4 |
|---|---|
| Automatika po nezvednutí | Zatím vypnutá |
| Zvuková výzva | Vlastní WAV/MP3 z Moje média, který P4 umí přehrát |
| Tlačítko nahrávání | Vzkaz nahrat 10 s |
| Tlačítko zrušení | Vzkaz zrusit |
| Obsazení záznamníku | Vzkaz zaneprazdnen — musí být zapnutý při nahrávání **i odesílání** |
| Stav záznamníku | Vzkaz stav |
| Důvod konce hovoru | VoIP Last Reason |

Názvy vycházejí z místního `esp32p4-intercom-vzkazy.yaml`. Pokud jsi entity přejmenoval, vyber jejich odpovídající názvy. Nevybírej jen „Mikrofon snímá“ místo obsazení záznamníku. Jestli potřebná entita chybí, neposílej místo ní jiný senzor; pošli seznam entit P4.

Výzvu si můžeš namluvit přes již funkční Hlasové vzkazy, například: **„Právě nemůžeme otevřít. Pokud chcete zanechat vzkaz, po skončení této zprávy mluvte. Máte deset sekund.“** Nahrávka začne přibližně sekundu po konci výzvy. Samostatný tón se negeneruje; chceš-li tón, musí být součástí zvoleného souboru. Výzva má být kratší než minutu, doporučeně několik sekund.

## První zkouška — jen tlačítky v HA

1. Zastav hudbu a ukonči hovory. P4 musí být `idle`, záznamník volný.
2. Otevři stránku **Dveřní zvonek** a stiskni **Výzva a nahrát vzkaz 10 s**.
3. U P4 musí zaznít celá výzva. Po jejím konci řekni zkušební vzkaz.
4. Na stránce očekávej stav nahrávání, odesílání a nakonec potvrzení uložení. V Hlasových vzkazech nebo Média → Moje média → vzkazy si nový soubor přehraj.
5. Vyzkoušej zrušení během výzvy: záznam nemá začít. Již zahájené odesílání D5 nelze vzít zpět; případně už uložený soubor tímto tlačítkem nesmažeš.

Sekvence čeká na skutečnou změnu přehrávače do přehrávání a následný konec. Samotné úspěšné zavolání přehrávače nestačí. Pokud HA začátek nebo konec přehrávání nezachytí, sekvence skončí chybou a záznam nespustí. To je nutné ověřit právě s tvou P4.

## Druhá zkouška — nezvednutý hovor

Po úspěšné ruční zkoušce v Konfigurovat zapni automatiku:

1. Stiskni **Zazvonit z P4** a žádný panel nepřijímej ani neodmítej. Po přirozeném timeoutu hovoru, návratu P4 do `idle` a novém důvodu `timeout` má následovat výzva a záznam.
2. Zazvoň znovu a hovor přijmi. Po jeho ukončení se výzva ani záznam spustit nesmí.
3. Zopakuj dva nezvednuté hovory za sebou. Každý má vytvořit právě jeden samostatný vzkaz.

Integrace hovor sama násilně neukončuje a nemění dobu vyzvánění. V místním D4 je `ringing_timeout: 30s`; skutečný konec skupinového hovoru závisí také na VoIP Stacku. Sledování jednoho pokusu má horní hranici 120 sekund.

Automatika se naváže jen na zazvonění spuštěné touto integrací, včetně akce `p4_doorbell.ring`. Neaktivuje se podle libovolného starého stavu `timeout`. Musí vidět vyzvánění na jednom z vybraných panelů, nezaznamenat přijetí a dostat nový důvod konce hovoru. Síťová chyba, nedostupnost zařízení, ruční zavěšení nebo odmítnutí nejsou automaticky považovány za nezvednutí.

Pokud se výzva nespustí, pošli stav P4, **VoIP Last Reason** a stav přijímacího telefonu po nezvednutém hovoru. Neznámé důvody konce hovoru nejsou automaticky převáděny na timeout. Pokud je záznamník obsazený nebo na P4 už hraje jiný zvuk, automatická výzva se také nespustí; stránka uvede důvod.

## Souběh a chyby

- Nový hovor má přednost. Integrace před spuštěním nahrávání znovu ověří klidový stav P4; záznamník D5 navíc sám zruší snímání, pokud začne hovor.
- Záznam se automaticky neopakuje při chybě sítě nebo uploadu. Při ztraceném potvrzení mohl server soubor uložit; nejdřív zkontroluj Hlasové vzkazy.
- Restart HA nerozběhne starou sekvenci znovu. Pokud P4 už nahrávala nebo odesílala, může tento krok samostatně dokončit.
- Nastavení měň mimo hovor a sekvenci; případné čekání ukonči tlačítkem Zrušit sekvenci vzkazu.
- Přístup zůstává omezen na správce HA. Oprávnění VoIP se neobcházejí. Zachovej fungující ID tlačítka P4 s `call`, které jsme ověřili v předchozí zkoušce.

## Ověřeno a neověřeno

Ve zdrojích ověřeno: záznamník používá 48 kHz / 16 bit / mono, délku nejvýše 10 s, stavy `Nahravam, nejvyse 10 s`, `Odesilam do HA`, `Ulozeno v HA`, potvrzení HTTP 201 a přednost hovoru. Viz místní `components/p4_voice_inbox/p4_voice_inbox.cpp`, funkce `record`, `save`, `loop`. Firmware se neměnil ani znovu nekompiloval.

Připnutý VoIP při novém hovoru maže předchozí důvod, takže další timeout může být novou událostí: [voip_fsm.cpp](https://github.com/n-IA-hane/esphome-voip-stack/blob/c693b4e75008afb5d2f584a09035aee2743a2210/esphome/components/voip_stack/voip_fsm.cpp#L628). Nastavení používá standardní [options flow Home Assistanta](https://developers.home-assistant.io/docs/config_entries_options_flow_handler/).

Lokálně prošlo **26 testů** logiky a zpracování chyb se simulovaným HA; také kontrola syntaxe JavaScriptu, Pythonu a JSON. Testy zahrnují úspěšný upload, HTTP 507, přijatý hovor, starý timeout, nedostupnost, dvojstisk, přerušení hovorem a chybějící potvrzení přehrání. Nejde o plný integrační test běžícího HA.

**Na skutečné sestavě zatím neověřeno:** D7 formulář, sledování přehrávače, automatická návaznost timeoutu a celý průchod výzva → nahrávka → uložení. Dosavadní jednotlivé části jsi už otestoval; jejich nové propojení teď vyžaduje výše uvedené zkoušky. Nic nebylo nasazeno ani flashováno.

## Co zůstává pro další etapu

Fyzické tlačítko zvonku a jeho opakovaný stisk pro záznam, režim nepřítomnosti, automatické snímky při detekci obličeje, navázání zaznamenání vzkazu na ručně zvolenou odpověď a upozornění uživateli. GPIO se v této etapě nevybírá.

Pro návrat nahraď integraci funkčním balíčkem D6 0.1.1 a restartuj HA. Nová nastavení v options se ve staré verzi nepoužijí. Neodstraňuj integraci ani její existující skupiny.
