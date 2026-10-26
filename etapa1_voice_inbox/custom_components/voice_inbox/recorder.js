/* No upload keys: all browser requests use the signed-in HA administrator. */
class VoiceInboxPanel extends HTMLElement {
  set hass(value) { this._hass = value; this.initialize(); }
  connectedCallback() { this.initialize(); }
  disconnectedCallback() {
    this.cancel();
    if (this.audioURL) URL.revokeObjectURL(this.audioURL);
    this.audioURL = null;
  }
  initialize() {
    if (!this.isConnected || !this._hass || this.shadowRoot) return;
    this.attachShadow({mode: "open"});
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Arial,sans-serif)}
        header{display:flex;align-items:center;gap:16px;padding:14px;background:var(--app-header-background-color);color:var(--app-header-text-color)}
        h1{font-size:22px;margin:0}main{max-width:680px;margin:24px auto;padding:0 18px}
        section{padding:24px;border:1px solid var(--divider-color);border-radius:16px;background:var(--card-background-color);margin-bottom:20px}
        p{line-height:1.5}label{display:block;margin-bottom:8px}select{padding:12px;width:100%;box-sizing:border-box;background:var(--card-background-color);color:inherit;border:1px solid var(--divider-color);border-radius:8px;font-size:16px}
        .buttons{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}button{cursor:pointer;border:0;border-radius:24px;padding:14px 20px;font-size:16px;background:var(--primary-color,#03a9f4);color:var(--text-primary-color,#fff)}
        button:disabled{opacity:.45;cursor:default}#stop{background:#b3261e;color:white}#cancel,#refresh{background:var(--secondary-background-color);color:inherit}
        #timer{font-size:32px;font-variant-numeric:tabular-nums}#status{padding:12px;border-radius:8px;background:var(--secondary-background-color);white-space:pre-wrap;overflow-wrap:anywhere}
        audio{width:100%}#file{overflow-wrap:anywhere;font-size:14px}small{color:var(--secondary-text-color)}
      </style>
      <header><ha-menu-button></ha-menu-button><h1>Hlasové vzkazy</h1></header>
      <main><section>
        <p>Nahraj vzkaz mikrofonem tohoto počítače nebo telefonu a ulož ho do Home Assistanta.</p>
        <label for="source">Uložit ke zdroji</label><select id="source"></select>
        <div class="buttons"><button id="start" disabled>Nahrát vzkaz</button><button id="stop" disabled>Zastavit a uložit</button><button id="cancel" disabled>Zrušit</button></div>
        <div id="timer">0:00 / 1:00</div><p id="status" role="status" aria-live="polite">Načítám…</p>
        <small>Nejvýše 60 sekund. Potom se nahrávka automaticky uloží. Mikrofon P4 se tímto tlačítkem nespouští.</small>
      </section><section>
        <h2>Poslední uložený vzkaz</h2><p id="quota"></p><p id="file">Zatím žádný vzkaz.</p>
        <audio id="audio" controls hidden></audio><div class="buttons"><button id="refresh">Obnovit a načíst vzkaz</button></div>
        <small>Přehrávač načítá soubor uložený v HA. Starší vzkazy najdeš v Média → Moje média → vzkazy.</small>
      </section></main>`;
    this.el = Object.fromEntries([...this.shadowRoot.querySelectorAll("[id]")].map(x => [x.id,x]));
    this.shadowRoot.querySelector("ha-menu-button").hass = this._hass;
    this.el.start.onclick = () => this.start();
    this.el.stop.onclick = () => this.stop();
    this.el.cancel.onclick = () => this.cancel();
    this.el.refresh.onclick = () => this.refresh();
    this.el.source.onchange = () => this.showLatest().catch(e => this.message(e.message));
    this.refresh(true);
  }
  message(text) { if (this.el) this.el.status.textContent = text; }
  controls() {
    if (!this.el) return;
    this.el.start.disabled = !!this.busy || !this.el.source.value;
    this.el.stop.disabled = this.busy !== "recording";
    this.el.cancel.disabled = !["recording", "starting"].includes(this.busy);
    this.el.source.disabled = !!this.busy;
    this.el.refresh.disabled = !!this.busy;
  }
  async request(path, options) {
    const response = await this._hass.fetchWithAuth(path, options);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const messages = {
        file_quota_reached: "Schránka je plná. Vzkaz nebyl uložen. Žádné soubory se automaticky nemažou.",
        insufficient_disk_space: "V HA není dost místa pro uložení vzkazu.",
        administrator_required: "Přihlas se jako správce Home Assistanta.",
        upload_busy: "Právě probíhá jiný upload. Zkus to později.",
        storage_unavailable: "Úložiště vzkazů není dostupné nebo do něj HA nemůže zapisovat.",
        unknown_source: "Zdroj už není nastavený. Obnov stránku."
      };
      throw new Error(messages[data.error] || `Požadavek selhal (${response.status}, ${data.error || "bez podrobností"}).`);
    }
    return response;
  }
  async refresh(initial = false) {
    try {
      const state = await (await this.request("/api/voice_inbox/browser/state")).json();
      if (!this.isConnected) return;
      this.state = state;
      const old = this.el.source.value;
      this.el.source.replaceChildren(...state.sources.map(source => {
        const option = document.createElement("option"); option.value = source; option.textContent = source; return option;
      }));
      if (state.sources.includes(old)) this.el.source.value = old;
      this.el.quota.textContent = `Uloženo ${state.count} z ${state.limit} vzkazů (všechny zdroje).`;
      await this.showLatest();
      if (initial) this.message(state.sources.length ? "Připraveno. Stiskni Nahrát vzkaz a povol mikrofon." : "Nejdřív přidej zdroj v integraci Voice Inbox.");
    } catch (e) { this.message(`Nelze načíst schránku: ${e.message}`); }
    finally { this.controls(); }
  }
  async showLatest(item = this.state?.latest[this.el.source.value]) {
    const generation = this.playGeneration = (this.playGeneration || 0) + 1;
    this.el.audio.pause(); this.el.audio.removeAttribute("src"); this.el.audio.hidden = true;
    if (this.audioURL) URL.revokeObjectURL(this.audioURL);
    this.audioURL = null;
    this.el.file.textContent = item ? item.file : "Tento zdroj zatím nemá uložený vzkaz.";
    if (!item) return;
    const response = await this.request(`/api/voice_inbox/browser/audio/${encodeURIComponent(item.source)}/${encodeURIComponent(item.file)}`);
    const blob = await response.blob();
    if (!this.isConnected || generation !== this.playGeneration) return;
    this.audioURL = URL.createObjectURL(blob);
    this.el.audio.src = this.audioURL; this.el.audio.hidden = false;
  }
  async start() {
    if (this.busy) return;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      this.message("Prohlížeč nepovoluje mikrofon na této adrese. Otevři HA přes HTTPS, například svou adresu Nabu Casa, a přihlas se jako správce."); return;
    }
    this.busy = "starting"; this.controls();
    const session = this.session = (this.session || 0) + 1;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}});
      if (this.session !== session || !this.isConnected) { stream.getTracks().forEach(t => t.stop()); return; }
      this.stream = stream;
      this.context = new AudioContext();
      await this.context.resume();
      if (this.session !== session || !this.isConnected) return;
      this.rate = this.context.sampleRate;
      this.chunks = []; this.frames = 0;
      this.sourceNode = this.context.createMediaStreamSource(stream);
      // Bounded PCM capture; a muted output keeps the processor active without feedback.
      this.processor = this.context.createScriptProcessor(4096, 1, 1);
      this.gain = this.context.createGain(); this.gain.gain.value = 0;
      this.processor.onaudioprocess = event => {
        if (this.busy !== "recording") return;
        const input = event.inputBuffer.getChannelData(0);
        const take = Math.min(input.length, this.rate * 60 - this.frames);
        if (take > 0) { this.chunks.push(input.slice(0, take)); this.frames += take; }
        const seconds = Math.floor(this.frames / this.rate);
        this.el.timer.textContent = `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,"0")} / 1:00`;
        if (this.frames >= this.rate * 60) this.stop();
      };
      this.sourceNode.connect(this.processor); this.processor.connect(this.gain); this.gain.connect(this.context.destination);
      this.busy = "recording"; this.controls(); this.message("Nahrávám — mluv. Potom stiskni Zastavit a uložit.");
      this.deadline = setTimeout(() => this.stop(), 60000);
    } catch (e) {
      if (this.session !== session) return;
      this.cleanup(); this.busy = null; this.controls();
      const reason = {NotAllowedError:"Povol mikrofon v oprávněních prohlížeče pro tuto adresu HA.", NotFoundError:"Počítač nebo telefon nemá dostupný mikrofon.", NotReadableError:"Mikrofon nelze otevřít. Může ho blokovat jiná aplikace."}[e.name];
      this.message(reason || `Mikrofon se nepodařilo spustit: ${e.message}`);
    }
  }
  cleanup() {
    clearTimeout(this.deadline);
    if (this.processor) this.processor.onaudioprocess = null;
    for (const node of [this.sourceNode,this.processor,this.gain]) node?.disconnect();
    this.stream?.getTracks().forEach(t => t.stop());
    this.context?.close().catch(() => {});
    this.stream = this.context = this.sourceNode = this.processor = this.gain = null;
  }
  cancel() {
    this.session = (this.session || 0) + 1;
    this.playGeneration = (this.playGeneration || 0) + 1;
    this.cleanup(); this.chunks = []; this.frames = 0;
    if (this.busy !== "saving") { this.busy = null; this.message("Nahrávání zrušeno. Vzkaz se neodeslal."); }
    this.controls();
  }
  async stop() {
    if (this.busy !== "recording") return;
    this.busy = "saving"; this.controls(); this.cleanup();
    this.message("Ukládám do Home Assistanta…");
    const source = this.el.source.value;
    let saved = false;
    try {
      if (!this.frames) throw new Error("Mikrofon neposlal žádný zvuk. Zkus nahrát delší vzkaz.");
      const offline = new OfflineAudioContext(1, Math.min(960000, Math.ceil(this.frames * 16000 / this.rate)), 16000);
      const buffer = offline.createBuffer(1, this.frames, this.rate);
      let offset = 0;
      for (const chunk of this.chunks) { buffer.copyToChannel(chunk,0,offset); offset += chunk.length; }
      this.chunks = [];
      const player = offline.createBufferSource(); player.buffer = buffer; player.connect(offline.destination); player.start();
      const samples = (await offline.startRendering()).getChannelData(0);
      const pcm = new ArrayBuffer(samples.length * 2), view = new DataView(pcm);
      samples.forEach((sample,i) => { const value = Math.max(-1,Math.min(1,sample)); view.setInt16(i*2, Math.round(value * (value < 0 ? 32768 : 32767)), true); });
      const response = await this.request("/api/voice_inbox/browser/upload", {method:"POST", headers:{"Content-Type":"application/octet-stream","X-Voice-Source":source,"X-Audio-Rate":"16000","X-Audio-Bits":"16","X-Audio-Channels":"1"}, body:pcm});
      const item = await response.json();
      if (response.status !== 201 || !item.file) throw new Error("Server nepotvrdil uložení vzkazu.");
      saved = true;
      if (!this.isConnected) return;
      this.message(`Uloženo v HA (${item.duration.toFixed(1)} s). Níže si vzkaz přehraj.`);
      await this.refresh();
      await this.showLatest(item);
    } catch (e) { this.message(`${saved ? "Vzkaz je uložený, ale přehrání se nepodařilo" : "Uložení nebylo potvrzeno"}: ${e.message}${saved ? "" : " Při výpadku spojení nejdřív obnov seznam, soubor už mohl být uložen."}`); }
    finally { this.chunks = []; this.busy = null; this.controls(); }
  }
}
if (!customElements.get("voice-inbox-panel")) customElements.define("voice-inbox-panel", VoiceInboxPanel);
