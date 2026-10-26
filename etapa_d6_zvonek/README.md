# Dveřní zvonek P4 — D6, první zkouška

Verze 0.1.0, 26. 10. 2026. Připraveno s pomocí OpenAI Codex.

Samostatná vlastní integrace přidává do HA stránku **Dveřní zvonek**, kameru P4, výběr místního telefonu, testovací zazvonění a přednastavenou zvukovou odpověď. Pro samotné hovory používá stávající VoIP Stack a jeho telefonní kartu. Není to ještě náhrada přenosové části VoIP.

## Co tato etapa umí

- Z P4 zavolat jednu skupinu s 1–3 přijímacími telefony prohlížečů (RPi/TouchKio, Zotac/TouchKio, PC).
- Ukázat kameru a původní telefonní kartu pro příjem a ukončení hovoru.
- Během vyzvánění převzít hovor pro přednastavenou odpověď, ukončit jej a poslat vybraný zvuk do přehrávače P4.
- Vytvořit tlačítko **Zazvonit**, senzor **Stav ovládání** a akci `p4_doorbell.ring` pro pozdější automatizaci.

Fyzické tlačítko, automatické chování při nepřítomnosti/nepřijetí, spuštění záznamu návštěvníka po výzvě, HuskyLens automatizace a obrazovky ESP jsou další etapy. Dosavadní funkční nahrávání P4 se nemění. Žádný firmware ani jeho piny tento balíček nemění.

## Instalace v HA

1. Rozbal `D6-zvonek-0.1.0.zip`. Složku `custom_components/p4_doorbell` zkopíruj do `/config/custom_components/p4_doorbell`. Stávající `voice_inbox` ani `voip_stack` nenahrazuj.
2. Restartuj Home Assistant. V **Nastavení → Zařízení a služby → Přidat integraci** vyhledej **Dveřní zvonek P4**.
3. Vyber zařízení P4 z ESPHome, jeho USB kameru, přehrávač a senzor **VoIP State**. Nevybírej stav nahrávání ani HuskyLens senzor. Název volajícího musí přesně odpovídat názvu ve VoIP, podle dosavadního logu `ESP32-P4`.
4. Vyber 1–3 existující **telefony prohlížečů** z VoIP Stacku. Vyber jejich logická zařízení v HA, nikoli ESP displeje nebo hostitelský počítač z jiné integrace.
5. Vyber zvukovou odpověď z **Moje média**. Můžeš si ji předem namluvit přes fungující stránku Hlasové vzkazy, například „Právě nemůžeme otevřít“. Vyber svou zkušební nahrávku; po přehrání se v této etapě ještě automaticky nespustí záznam návštěvníka.
6. Otevři **Dveřní zvonek** v postranním menu. Klikni **Zapojit vybrané panely**. Tím se každému přidá skupina `P4-dvere-…`; ostatní skupiny zůstanou zachované. Na přijímacích telefonech vypni automatický příjem, pokud na něj stránka upozorní.

První verze je určena uživateli s právy správce HA. Používá jeho přihlášení, nemá vlastní heslo ani upload klíč a neotevírá nové síťové porty.

## Vyzkoušení tlačítky

1. Na každém přijímacím panelu otevři novou stránku a v **Tento displej přijímá jako** vyber jeho vlastní telefon. Výběr se uloží v tomto prohlížeči. Jeden logický telefon nepoužívej současně na více fyzických panelech. Pro test zavři další karty ovládající stejný telefon.
2. Pokud karta VoIP nebo kamera hlásí, že není načtená, otevři v téže kartě prohlížeče stávající dashboard Intercom a vrať se. Integrace používá přesně stávající modul VoIP, aby nevytvářela druhý zvukový engine.
3. Stiskni **Zazvonit z P4**. Vybrané panely mají vyzvánět a zobrazit kameru. Na jednom přijmi hovor pomocí původní telefonní karty. Ověř řeč oběma směry a ukonči hovor. Ostatní vyzvánění má ukončit VoIP Stack.
4. Zazvoň znovu a během vyzvánění stiskni **Přehrát: …**. Očekávání: vyzvánění skončí, P4 se vrátí do `idle` a z jejího reproduktoru zazní vybraný soubor. Stav „Odpověď odeslána“ potvrzuje odeslání akce přehrávači, nikoli slyšitelné přehrání.
5. Na dvou panelech vyzkoušej téměř současné přijetí hovoru a stisk odpovědi. Pokud vyhrál běžný příjem, nesmí druhý panel zavěsit tento hovor ani přehrát odpověď.

Prohlížeč potřebuje povolený mikrofon a bezpečný kontext (obvykle HTTPS), stejně jako dosavadní VoIP karta. Nejprve testuj na již funkčních přijímacích telefonech. Kamera běží na otevřených stránkách; při více displejích sleduj plynulost zvuku i obrazu.

Při problému pošli text chyby z nové stránky, stav **VoIP State** P4, stav telefonu a odpovídající protokol HA. Pokud převzetí hovoru nebylo potvrzené, ověř telefonní kartu a případně na ní zavěs. Integrace v nejistotě úmyslně nezavěšuje P4 naslepo. Během první zkoušky neiniciuj další nesouvisející hovory s P4.

## Ověření a hranice

Ověřeno lokálně: 10 testů skutečné řídicí logiky se simulovaným HA, syntaxe Pythonu/JavaScriptu a JSON, čistota ZIP. Testy zahrnují zachování skupin, dvojstisk, blokování automatického příjmu, chybný telefon/identifikátor hovoru, prohru při souběžném příjmu a zákaz přehrání při neuvolněné P4.

**Neověřeno v běžícím HA:** instalační průvodce, vykreslení panelu, skutečné přepnutí skupin, skupinový hovor a přehrání odpovědi. Home Assistant ani další balíčky nebyly na PC instalovány; nejde o úplné integrační testy HA. Do HA nebylo nic nasazeno a na P4 nic nahráno.

Referenční veřejná rozhraní byla kontrolována v lokálním VoIP Stacku 2026.10.1, commit `6581cfea712d0e13bf88c5aff3fa97b9e27123ab`. Pokud instalovaná verze vystavuje jiné entity, stránka operaci odmítne s chybou. Připnuté komponenty ESP zůstávají stejné.

- [Akce VoIP](https://github.com/n-IA-hane/esphome-intercom/blob/6581cfea712d0e13bf88c5aff3fa97b9e27123ab/custom_components/voip_stack/services.yaml)
- [Entity skupin](https://github.com/n-IA-hane/esphome-intercom/blob/6581cfea712d0e13bf88c5aff3fa97b9e27123ab/custom_components/voip_stack/text.py)
- [Telefonní karta](https://github.com/n-IA-hane/esphome-intercom/blob/6581cfea712d0e13bf88c5aff3fa97b9e27123ab/custom_components/voip_stack/frontend/voip-stack-card.js)

## Návrat a změna nastavení

První verze nemá editor konfigurace. Pro jiné přijímače nebo jinou zvukovou odpověď integraci odeber a znovu přidej. Před odebráním odstraň v nastavení skupin přijímacích telefonů pouze její skupinu `P4-dvere-…`, kterou najdeš také v atributu senzoru Stav ovládání. Ostatní skupiny zachovej. Integrace při odebrání skupiny automaticky nemaže. Odebírej ji mimo aktivní hovor.

Původní Intercom a Hlasové vzkazy zůstávají použitelné samostatně.

## Pro vývojáře

Testy se spouštějí standardním Pythonem: `python -B tests/test_controller.py`. Nepotřebují venv ani instalaci HA, protože simulují jeho rozhraní; toto není krok pro používání zvonku.
