# Etapa 1 — Voice Inbox 0.3.1 pro HA Core 2026.10.3

## Oprava více zdrojů (0.3.1)

Opravuje chyby `method GET is already registered` a
`async_config_entry_first_refresh ... ConfigEntryState.LOADED` při přidání
nebo společném startu více zdrojů, například `annahp`, `panel7`, `p4`.

**Aktualizace:** z balíčku `voice-inbox-stage1-0.3.1.zip` nahraď celou složku
`/config/custom_components/voice_inbox`, potom **restartuj celý Home Assistant**
a obnov stránku prohlížeče. Pouhé znovunačtení integrace nestačí k odstranění
již registrovaných HTTP cest staré verze. Zdroje znovu nezakládej, jejich klíče
neměň a nahrávky nemaž. Po restartu ověř, že všechny tři zdroje mají načtené
entity a lze je vybrat na stránce Hlasové vzkazy.

Společná registrace HTTP cest a panelu je chráněná zámkem. Sdílený koordinátor
má explicitně `config_entry=None`, běžný refresh a ukončení při vypnutí HA;
odpojení prvního zdroje tak nevypíná koordinátor ostatních. Selhání nastavení
zdroje odstraňuje jeho dočasnou autorizaci a načtené platformy před dalším pokusem.
Firmware P4, endpoint uploadu, klíče, kvóta i uložené soubory se touto opravou nemění.

Prošlo 8 cílených regresních kontrol s náhradami HA API (souběh tří zdrojů,
opakovaná registrace, unload/reload a zotavení z chyby). Celý start ve skutečném
HA a jeho middleware zde ověřené nejsou. K aktualizaci nepotřebuješ žádné
testovací prostředí ani skripty.

## Vyzkoušení tlačítkem přímo v HA

Pro tento postup nepotřebuješ Python, virtuální prostředí, terminál ani skripty.

1. Rozbal `voice-inbox-stage1.zip`. Z něj zkopíruj **celou složku**
   `custom_components/voice_inbox` do `/config/custom_components/voice_inbox`
   svého HA; nahraď předchozí soubory integrace. Ne do `addon_configs`.
2. Restartuj Home Assistant a obnov stránku prohlížeče (případně Ctrl+F5).
   Existující konfiguraci zdroje nech nastavenou, integraci nepřidávej znovu.
3. Přihlas se jako správce a v levém menu otevři **Hlasové vzkazy**.
   Přímá cesta je `/voice-inbox` za adresou tvého HA.
4. Vyber zdroj, stiskni **Nahrát vzkaz**, povol mikrofon a promluv.
5. Stiskni **Zastavit a uložit**. Úspěch poznáš podle **Uloženo v HA**.
   Dole stiskni přehrávání. Zvuk se načítá ze souboru uloženého v HA,
   nikoli z původního záznamu v prohlížeči.

**Používá se mikrofon PC nebo telefonu, na kterém máš otevřený HA.** P4 tímto
tlačítkem nenahrává; tento krok ověřuje přijímač a ukládání. Mikrofon P4
budeme připojovat ve firmware až v další etapě.

Prohlížeč pro mikrofon potřebuje zabezpečenou adresu: použij svou **HTTPS adresu
Nabu Casa**. Běžné `http://192.168…` mikrofon obvykle nepovolí. Už nastavená
výjimka prohlížeče může fungovat také. Stránka odepřený přístup vysvětlí.

Záznam trvá nejvýše 60 sekund, pak se automaticky odešle. **Zrušit** ukončí
nahrávání bez odeslání. Během nahrávání a ukládání nech stránku otevřenou
a telefon nezamykej. Přenos do HA probíhá až po zastavení; záznam se ukládá jako
WAV, mono 16 bit / 16 kHz. Převod zajistí stránka. Limity a kvóta platí stejně
jako pro upload z ESP. Nic se automaticky nemaže.

Pokud menu chybí, ověř přihlášení správce, restart HA a že integrace Voice Inbox
nemá chybu nastavení. Přímá cesta neobejde neúspěšné načtení integrace.

### Přístup prohlížeče a ESP

Nové cesty `/api/voice_inbox/browser/state`, `/browser/upload` a
`/browser/audio/<zdroj>/<soubor>` pod prefixem `/api/voice_inbox` vyžadují
přihlášení HA **a oprávnění správce**. Fungují i přes Nabu Casa; žádné klíče
zdrojů se do stránky neposílají. Správce může vybrat kterýkoli nastavený zdroj.
Nahrávání prohlížečem ověřuje stejnou validaci a atomické ukládání jako ESP,
ale neověřuje jeho LAN přístup ani klíč.

Původní `/api/voice_inbox/upload` pro zařízení má dál samostatný klíč pro zdroj,
omezení na LAN a stejný limit chybných klíčů. Jeho zabezpečení se neuvolnilo.
JavaScript stránky je veřejný statický soubor bez tajných údajů; zvuk veřejný není.

Nové soubory: `custom_components/voice_inbox/browser.py` a `recorder.js`.
Změněny: registrace integrace a manifest (0.3.0), sdílení příjmu v `http.py`,
ověřené čtení uloženého souboru v `storage.py`, návod a přehled ověření.

Podklady API:
[vlastní panel HA](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/components/panel_custom/__init__.py),
[autentizace HTTP view](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/helpers/http.py),
[mikrofon prohlížeče](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

**Živé ověření této nové stránky v tvém HA zatím neproběhlo.** Níže uvedené
skripty a testovací prostředí jsou pouze pro vývojáře; k použití stránky nejsou potřeba.

Oprava 0.1.1: nepředpokládá klíč `local`. Preferuje cestu `/media` pod libovolným
identifikátorem HA; jinak zvolí `local`, případně jediný nakonfigurovaný mediální
adresář. Používá skutečný identifikátor i v odkazu na soubor. Více nejednoznačných
adresářů nebo chybějící mapování odmítne. Při použití jiného adresáře se ukládá
do jeho podsložky `vzkazy`.

Samostatná nová podsložka projektu. Žádný firmware ani stávající přijímač D2
se nemění. Integrace není nasazená do HA. Vytvořeno s pomocí ChatGPT/Codex.

## Stav ověření a hranice

- Python na PC: 3.14.2. Standardní testy validace, ukládání a přístupu byly spuštěny.
- `tests/test_http.py` obsahuje skutečné aiohttp HTTP testy s importy HA. Zde nebyly
  spuštěny: pytest, aiohttp a HA nejsou nainstalované. Nic jsem neinstaloval.
- Tyto HTTP testy používají malý testovací objekt HA; neověřují celý start Core,
  config flow v UI ani middleware skutečného HA. Config flow a provoz za
  Supervisorem/Nabu Casa čekají na kontrolovaný integrační test.
- Žádná univerzální garance funkčnosti před těmito testy. Nevystavovat port na routeru.
- Verze 0.2.0 má upload, události, entity a upozornění na kvótu; nemá vlastní služby, přepis ani mazání.
- Při ztrátě odpovědi po uložení může opakovaný upload vytvořit druhý soubor.
  Idempotence není součástí této verze; automatické opakování zatím nepoužívat.

## Soubory

`custom_components/voice_inbox/`: `manifest.json`, `__init__.py`, `config_flow.py`,
`const.py`, `http.py`, `storage.py`, `access.py`, `strings.json`, `translations/cs.json`.
`tests/test_storage.py`, `tests/test_http.py`, `tests/test_config_flow.py`; `tools/check_environment.py`,
`tools/make_sample.py`; `requirements-test.txt`, `pytest.ini`, `VALIDATION.md`, tento návod.

## Ochrana před vzdáleným přístupem

Endpoint POST `/api/voice_inbox/upload` používá `HomeAssistantView` s vlastní
autorizací. Nemá download, GET ani službu obecného přístupu do HA.

1. `is_cloud_connection(hass)` odmítne Nabu Casa Remote UI před čtením těla.
2. Odmítají se hlavičky `Forwarded` a `X-Forwarded-For/Host/Proto`.
3. `request.remote` musí být shodné s IP skutečného TCP protějšku a musí patřit
   do explicitně povolené sítě zdroje. Ve flow lze povolit jen RFC1918 IPv4 nebo ULA IPv6.
4. Klíč zdroje se posílá v `X-Voice-Key`, ne v URL a ne jako HA access token.
   V config entry se uchovává jen SHA256 otisk. Zdroj musí přesně odpovídat klíči.
5. Po 5 chybných klíčích z jedné IP za 60 s se vrací 503; globální limit je
   50 chybných pokusů za 60 s. Evidence má nejvýše 256 IP. Limit po restartu zaniká.
6. Žádné hlavičky, klíče ani těla se z integrace nelogují. To není záruka za
   vlastní proxy nebo externí síťové debug logy. Nepoužívat curl `-v` ani trace.

Ochrana je fail-closed: legitimní LAN přístup přes proxy se může také odmítnout.
V nové HA síťové cestě může být přítomen Supervisor proxy; přímé porovnání je
nutné ověřit z PC. Pokud upload vrací 401 při správném klíči, nesnižovat ochranu:
nejprve zjistit skutečnou trasu. Nabu Casa může požadavek dovést k view, ale view ho
nesmí přijmout ani uložit. Přímo přes cloud proto ověříme očekávané odmítnutí.
Tato politika není ochranou proti přetížení celého HTTP serveru před handlerem.

HTTP v LAN přenáší klíč a audio bez šifrování. Pokud přímý LAN endpoint nabízí
ověřitelné HTTPS, použít jej. Nepoužívat `-k` / vypnutí kontroly certifikátu.
Klíč je přenosný tajný údaj, nikoli ochrana proti odposlechu LAN.

Ověřené zdroje verze 2026.10.3:
- [Rozpoznání cloudu](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/helpers/network.py#L371)
- [Zpracování proxy a Nabu Casa](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/components/http/forwarded.py#L73)
- [HTTP view a autorizace](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/helpers/http.py#L126)
- [16 MiB limit serveru](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/components/http/server.py#L69)
- [Zápis /media v Supervisoru](https://github.com/home-assistant/supervisor/blob/2026.10.3/supervisor/docker/homeassistant.py#L144)

## Protokol

POST na místní HA adresu a skutečný port, cesta `/api/voice_inbox/upload`.
Povinné hlavičky:

| Hlavička | Hodnota |
|---|---|
| X-Voice-Source | Konfigurovaný zdroj, například `dvere` |
| X-Voice-Key | Náhodný samostatný klíč, 64 malých hexadecimálních znaků |
| X-Audio-Rate | `16000` nebo `48000` |
| X-Audio-Bits | `16` |
| X-Audio-Channels | `1` |
| Content-Type | `application/octet-stream` pro signed little-endian PCM; `audio/wav` pro WAV |
| Content-Length | Skutečná délka těla; curl ji u souboru doplní |

Maximálně 8 MiB na tělo, 60 s audia, příjem těla nejvýše 30 s. Chunked transfer
a komprese těla nejsou podporované. WAV musí být RIFF/WAVE s nekomprimovaným
16bitovým mono PCM, jeho parametry musí souhlasit s hlavičkami. Neplatná délka
RIFF nebo neúplné vzorky se odmítají. WAV je uložen znovu jako kanonický PCM WAV
bez původních metadat. Názvy vstupních souborů se nepřebírají.

Ukládá se `/media/vzkazy/<autorizovaný_zdroj>/<UTC čas>_<UUID>.wav`.
Povoleno 100 WAV souborů dohromady pro všechny zdroje a rezerva 32 MiB na disku.
Kvóta se kontroluje pod zámkem. Nejvýše jeden upload na zdroj a dva celkem.
Adresář spravuje integrace; nevytvářet v něm symlinky ani jej souběžně nepřesouvat.
Diskový zápis a validace WAV běží v executor jobu. HTTP tělo je omezeně bufferováno
v RAM HA; nejde o zapisování po síti přímo do konečného WAV. Krátce může existovat
více kopií audia, proto není paměť HA omezena pouze velikostí jediného požadavku.
Soubor `.part` je fsyncnutý a přejmenovaný ve stejném adresáři. Při běžné chybě se
odstraní; po výpadku napájení může `.part` zůstat. Plná odolnost vůči výpadku napájení
ani atomická transakce mezi souborem a HA event bus nejsou garantované.

| Stav | Význam |
|---|---|
| 201 | WAV uložen; JSON: source, file, relative_path, duration, sample_rate, time, bytes, media_content_id |
| 400 | Vadná metadata/tělo, chybějící délka, přerušený nebo pomalý upload |
| 401 | Cloud/proxy/nepovolená LAN, neznámý zdroj nebo chybný klíč |
| 413 | Více než 8 MiB nebo 60 sekund |
| 415 | Nepodporovaný formát, frekvence, kanály nebo nesoulad WAV |
| 503 | Obsazeno, limit autentizačních pokusů, úložiště nedostupné či interní chyba |
| 507 | Kvóta souborů, málo místa nebo disková kvóta |

Neúspěch může také nastat před view (proxy, HTTP parser, síť). Při odpojeném klientu
nelze doručení chybové odpovědi zaručit. Zařízení má uznat pouze 201 a platný JSON.
Po uložení vznikne událost `voice_inbox_saved` se stejnými daty jako odpověď.
Event bus není trvalá fronta oznámení; soubor je hlavním trvalým výsledkem.

## Testy na PC — bez instalace do tvého HA

Z adresáře `etapa1_voice_inbox` lze na Windows spustit bez dalších balíčků:

```powershell
py -3.14 -m unittest discover -s tests -p test_storage.py -v
```

Plné HTTP testy: Linux/WSL, Python **>=3.14.2** (doporučen 3.14.x), samostatné
virtuální prostředí, balíčky podle `requirements-test.txt`. Core je připnut na
2026.10.3, jeho závislost aiohttp na 3.14.5; pytest 8.3 až 9.x,
pytest-asyncio 1.x a pytest-aiohttp 1.x. Řešení závislostí pipem nebylo zde provedeno.
Balíček pytest-homeassistant-custom-component není pro tyto testy potřeba.

Následující příkazy jsou pouze návod pro uživatele, nebyly spuštěny:

```sh
python3.14 -m venv .wsl-venv
. .wsl-venv/bin/activate
python -m pip install -r requirements-test.txt
python tools/check_environment.py
python -m pytest -q
```

**Jedním příkazem ověříš prostředí:** `python tools/check_environment.py`.
Vrací 0, pokud odpovídá Python, Core/aiohttp a jsou dostupné testovací balíčky
v Linuxu. Skript nic neinstaluje.

## Nasazení — až po výslovném potvrzení

Nejprve dokončit HTTP testy. Poté zkopírovat pouze adresář
`custom_components/voice_inbox` přes Samba do `/config/custom_components/voice_inbox`.
Pokud už tam stejná integrace existuje, zastavit a vyřešit aktualizaci; nepřepisovat
naslepo. Restartovat Core. Nastavení → Zařízení a služby → Přidat integraci →
Voice Inbox / Hlasové vzkazy. Každý zdroj se přidává samostatně.

Zadat ID zdroje, skutečnou LAN síť a vlastní náhodný 256bitový klíč (64 hex znaků).
Použít generátor správce hesel; pro druhý zdroj jiný klíč. Ve firmware později
výhradně `!secret`. V této etapě se firmware nemění. Klíč si bezpečně uschovat,
integrace ukládá jen otisk. Rotace v první verzi: odebrat neaktivní zdroj a přidat
znovu s novým klíčem. Současné nahrávání blokuje odebrání zdroje.

## Ruční test z PC — až po schváleném nasazení

V adresáři této etapy vytvořit testovací sekundový WAV:

```powershell
py -3.14 tools/make_sample.py
```

Následující PowerShell příklad posílá stejný endpoint a protokol, jaký později
použije ESP. Klíč zadáš skrytě; není součástí historie příkazů ani argumentů curl.
Proměnnou adresy nastav podle ověřené místní adresy a portu, ne adresy Nabu Casa.

```powershell
$inboxUrl = Read-Host 'Mistni URL vcetne portu a /api/voice_inbox/upload'
$inboxSecret = Read-Host 'Klic zdroje dvere' -AsSecureString
$inboxKey = [System.Net.NetworkCredential]::new('', $inboxSecret).Password
try {
  $inboxConfig = @"
url = "$inboxUrl"
request = "POST"
header = "X-Voice-Source: dvere"
header = "X-Voice-Key: $inboxKey"
header = "X-Audio-Rate: 16000"
header = "X-Audio-Bits: 16"
header = "X-Audio-Channels: 1"
header = "Content-Type: audio/wav"
data-binary = "@sample-16000.wav"
"@
  $inboxConfig | curl.exe --config - --silent --show-error --include --max-time 40
} finally {
  $inboxKey = $null
  $inboxConfig = $null
  $inboxSecret.Dispose()
}
```

Zadávat jen důvěryhodnou HA URL; neobsahuje klíč. Nepoužívat transcript/verbose
logování shellu. Nulování proměnné negarantuje vymazání všech kopií z paměti PC.

Očekávání: 201, JSON s duration 1 a sample_rate 16000, jeden WAV v médiích.
Před uploadem v Nástroje pro vývojáře → Události poslouchat `voice_inbox_saved`.
Soubor otevřít v Média → Moje média → vzkazy → dvere. Zvuk je krátký tón.
Stejný test přes Nabu Casa musí skončit 401 (nebo odmítnutím již před integrací),
bez nového souboru a události. Negativní pokusy provádět až po úspěšném LAN testu;
po pěti špatných klíčích počkat alespoň 60 sekund.

## Co zjistit u sebe

- Skutečnou LAN adresu, port a případnou proxy mezi ESP/PC a Core. URL z Nabu Casa
  není upload URL. Nepředpokládat automaticky port 8123.
- Síť ESP i testovacího PC (správný CIDR), případné oddělené VLAN.
- Že media source `local` míří na `/media`, adresář je zapisovatelný a má místo.
  Chybějící nebo nejednoznačné mapování integrace odmítne při inicializaci.
- Že domácí HTTP/HTTPS cesta dovolí skutečné přímé připojení; při 401 neobcházet
  ochranu, nejprve zjistit důvod a případně návrh bezpečně upravit.
- Ověřit, že Nabu Casa upload opravdu neuloží. Toto živé ověření zatím neproběhlo.
- Až po těchto výsledcích schválit etapu 2. Zde se práce zastavuje.


## Ladění chybných klíčů — ochranu nevypínat

Po 5 chybných klíčích z jedné IP během 60 sekund je blokovaný i upload se
správným klíčem. Odpověď je **503** a JSON obsahuje
`authentication_rate_limited`; hlavička `Retry-After` doporučuje 60 sekund.
Při ladění ESP zastavit automatické pokusy, opravit zdroj a klíč a počkat
**60 sekund od posledního chybného pokusu**, potom poslat jediný upload.
Nejde o obsazený přijímač: ten vrací také 503, ale s chybou `upload_busy`.

Přesná implementace používá klouzavé 60sekundové okno, nikoli nový pevný
60sekundový zákaz od pátého pokusu. Blokování může skončit dříve, jakmile
nejstarší chybný pokus opustí okno. Vyčkání 60 sekund je bezpečný postup.
Platí také globální limit 50 chybných pokusů za 60 sekund; v takovém případě
může stejnou odpověď dostat i jiná IP. Nastavení ochrany se nemění.

## Obsah distribučního balíčku

ZIP se vytváří výslovným seznamem souborů, nikoli zabalením celého pracovního
adresáře. Neobsahuje virtuální prostředí, `__pycache__`, `.pyc`, nahrávky ani
přístupové údaje. Windows `.test-venv` zůstává na PC beze změn; WSL návod
používá samostatné `.wsl-venv`. Nové testy se na žádost uživatele odkládají.

## Přehled v HA — verze 0.2.0

Po uživatelem schválené aktualizaci složky integrace a restartu Core se u každého
nakonfigurovaného zdroje objeví zařízení „Vzkazy <zdroj>“ se čtyřmi entitami:

| Entita | Co ukazuje |
|---|---|
| Poslední vzkaz | Čas posledního WAV daného zdroje; atributy file a media_content_id |
| Počet vzkazů celkem | Počet WAV všech zdrojů ve společném úložišti |
| Zaplnění společné kvóty | Celkový počet / 100, v procentech |
| Společná kvóta plná | Problém zapnutý při nejméně 100 WAV |

Společné ukazatele jsou u každého zařízení stejné; nejde o samostatnou kvótu
100 souborů pro každý zdroj. Přesná entity_id přidělí HA, nejsou zde předpokládána.
Entity lze přidat do dashboardu běžným výběrem entity. Čas posledního vzkazu se
obnovuje podle času změny souboru v UTC; při ručním kopírování souborů se tedy
může lišit od původního času nahrávání. Bez nahrávky je poslední vzkaz neznámý.
Při selhání čtení úložiště jsou entity nedostupné, neukazují falešnou nulu.

Stav se načte při inicializaci, po uploadu a po minutě (včetně změn provedených
ručně mimo integraci). Nahrávky se přehrávají v Média → Moje média → vzkazy → zdroj.
Entita samotná není audio přehrávač; media_content_id je identifikátor pro akci
media_player.play_media, nikoli veřejný odkaz bez přihlášení.

## Kvóta a oznámení — verze 0.2.0

Výchozí i aktuální limit zůstává 100 WAV společně. ŽÁDNÉ AUTOMATICKÉ MAZÁNÍ.
Od 80 % se vytvoří persistentní oznámení v HA. Další změny počtu aktualizují
stejné oznámení s ID voice_inbox_quota. Při obnovení pod 80 % jej integrace zruší.
Pokud uživatel oznámení zavře, znovu se objeví při změně počtu, odmítnutí uploadu
nebo restartu, ne při každém minutovém čtení stejného stavu.

Při dosažení 80 % vznikne voice_inbox_quota_warning (count, limit).
Také při startu s již zaplněným úložištěm vznikne upozornění.
Při odmítnutí uploadu z důvodu počtu souborů vznikne voice_inbox_quota_rejected
(source, count, limit, reason=file_quota_reached, inventory_available).
Persistentní oznámení jasně řekne, že NOVÝ VZKAZ NEBYL ULOŽEN. HTTP zůstává 507.
Pokud inventář nelze znovu načíst, count může být poslední známá hodnota a
inventory_available je false. Žádná událost ani oznámení neobsahuje klíč.
Upozornění nezachrání odmítnutý záznam; opakování odeslání z ESP je etapa 2.
Chyba pouhého obnovení přehledu nemění úspěšně uložený upload na neúspěšný.

Nastavitelný limit, evidence poslechnutí a ručně potvrzené mazání zůstávají pro
etapu 4. Stáří souboru samo není souhlas se smazáním neposlechnutého vzkazu.

## Ověření této aktualizace

Na přání uživatele NEBYLY spuštěny žádné nové testy. Proběhla pouze kontrola
syntaxe Python/JSON a obsahu ZIP. Entity, životní cyklus HA a oznámení jsou nově
implementované a NEOVĚŘENÉ v běžícím HA. Předchozí úspěšné testy z VALIDATION.md
nejsou důkazem funkčnosti verze 0.2.0. Nic nebylo nasazeno ani nahráno na ESP.

Nové soubory: coordinator.py, entity.py, sensor.py, binary_sensor.py v adresáři
custom_components/voice_inbox. Upravené: __init__.py, http.py, storage.py,
manifest.json a dokumentace. Firmware, síťové omezení a ochrana klíčů beze změny.
