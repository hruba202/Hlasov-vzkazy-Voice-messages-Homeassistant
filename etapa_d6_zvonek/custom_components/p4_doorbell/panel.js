class P4DoorbellPanel extends HTMLElement {
  set hass(value) {
    this._hass = value;
    if (this.phoneCard) this.phoneCard.hass = value;
    if (this.cameraCard) this.cameraCard.hass = value;
    if (this.menu) this.menu.hass = value;
    this.initialize();
  }
  connectedCallback() { this.initialize(); }
  disconnectedCallback() { clearTimeout(this.timer); this.timer=null; }
  initialize() {
    if (!this.isConnected || !this._hass) return;
    if (this.shadowRoot) { if (!this.timer) this.refresh(); return; }
    this.attachShadow({mode:"open"});
    this.shadowRoot.innerHTML = `
      <style>
      :host{display:block;color:var(--primary-text-color);font-family:Arial,sans-serif}
      header{display:flex;align-items:center;gap:15px;padding:16px;background:var(--app-header-background-color);color:var(--app-header-text-color)}
      h1{font-size:22px;margin:0}main{max-width:1050px;margin:22px auto;padding:0 16px}
      .grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:750px){.grid{grid-template-columns:1fr}}
      section{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:16px;padding:20px;margin-bottom:20px}
      select{width:100%;padding:12px;font-size:16px;background:var(--card-background-color);color:inherit;border:1px solid var(--divider-color);border-radius:8px}
      button{border:0;border-radius:24px;padding:14px 20px;font-size:16px;background:var(--primary-color,#03a9f4);color:var(--text-primary-color,#fff);cursor:pointer;margin:8px 8px 0 0}button:disabled{opacity:.45;cursor:default}
      p{line-height:1.5}#error{color:var(--error-color,#f44336);white-space:pre-wrap}#issues{white-space:pre-wrap;color:var(--secondary-text-color)}
      #status{font-weight:bold}#camera{min-height:150px}small{color:var(--secondary-text-color)}
      </style>
      <header><ha-menu-button></ha-menu-button><h1>Dveřní zvonek</h1></header>
      <main><div class="grid"><section><h2>U dveří</h2><div id="camera"></div><p id="status">Načítám…</p><p id="door"></p></section>
      <section><label for="phone">Tento displej přijímá jako</label><p><select id="phone"></select></p>
      <div id="call"></div><p><button id="reply" disabled>Přehrát odpověď u dveří</button></p>
      <small>Hovor přijmi tlačítkem na telefonní kartě. Přednastavená odpověď převezme vyzvánění, zavěsí a přehraje zvolený soubor na P4.</small></section></div>
      <section><h2>Ruční zkouška</h2><button id="enroll">Zapojit vybrané panely</button><button id="ring" disabled>Zazvonit z P4</button>
      <p id="issues"></p><p id="error" role="alert"></p><small>Na každém fyzickém panelu vyber jeho vlastní telefon. Tato verze vyžaduje správce HA. Mikrofon prohlížeče vyžaduje HTTPS.</small></section></main>`;
    this.el = Object.fromEntries([...this.shadowRoot.querySelectorAll("[id]")].map(e=>[e.id,e]));
    this.menu=this.shadowRoot.querySelector("ha-menu-button"); this.menu.hass=this._hass;
    this.el.phone.onchange=()=>{ try{localStorage.setItem("p4-doorbell-phone",this.el.phone.value);}catch{} this.mountPhone().catch(e=>this.error(e)); };
    this.el.enroll.onclick=()=>this.command("enroll");
    this.el.ring.onclick=()=>this.command("ring");
    this.el.reply.onclick=()=>{const p=this.data.phones.find(p=>p.device_id===this.el.phone.value); if(p)this.command("reply",{device_id:p.device_id,call_id:p.call_id,visit:this.data.visit});};
    this.refresh();
  }
  error(e) { if(this.el)this.el.error.textContent=e.message || String(e); }
  async api(options) {
    const response=await this._hass.fetchWithAuth("/api/p4_doorbell/control",options);
    const body=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(body.error || `HA vrátilo chybu ${response.status}. Přihlas se jako správce.`);
    return body;
  }
  async command(action,extra={}) {
    if(this.sending)return;
    this.sending=true; this.el.error.textContent=""; this.updateButtons();
    try { await this.api({method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action,...extra})}); }
    catch(e){this.error(e);}
    finally{this.sending=false;await this.refresh();}
  }
  updateButtons(){
    if(!this.data)return;
    const busy=this.sending||this.data.busy;
    this.el.ring.disabled=busy||this.data.issues.length>0||this.data.door_state.toLowerCase()!=="idle";
    this.el.enroll.disabled=busy||this.data.door_state.toLowerCase()!=="idle";
    const p=this.data.phones.find(p=>p.device_id===this.el.phone.value);
    this.el.reply.disabled=busy||!this.data.visit||p?.state!=="ringing";
  }
  async refresh(){
    clearTimeout(this.timer);this.timer=null;
    if(!this.isConnected || this.refreshing)return;
    this.refreshing=true;
    try{
      this.data=await this.api(); if(!this.isConnected)return;
      this.el.status.textContent=this.data.status;
      this.el.door.textContent=`Stav telefonu P4: ${this.data.door_state}`;
      this.el.issues.textContent=this.data.issues.join("\n");
      this.el.reply.textContent=`Přehrát: ${this.data.reply_label}`;
      const signature=JSON.stringify(this.data.phones.map(p=>[p.device_id,p.name]));
      if(signature!==this.phoneSignature){
        let previous=this.el.phone.value;try{previous ||= localStorage.getItem("p4-doorbell-phone");}catch{}
        this.el.phone.replaceChildren(...this.data.phones.map(p=>{const o=document.createElement("option");o.value=p.device_id;o.textContent=p.name;return o;}));
        if(this.data.phones.some(p=>p.device_id===previous))this.el.phone.value=previous;
        this.phoneSignature=signature;
      }
      await this.mountCamera(); await this.mountPhone(); this.updateButtons();
    }catch(e){this.error(e);}
    finally{this.refreshing=false;if(this.isConnected)this.timer=setTimeout(()=>this.refresh(),2000);}
  }
  async mountCamera(){
    if(this.cameraCard)return;
    if(!window.loadCardHelpers)throw new Error("Nejdřív otevři běžný dashboard HA a potom se vrať ke zvonku.");
    const helpers=await window.loadCardHelpers();
    this.cameraCard=helpers.createCardElement({type:"picture-entity",entity:this.data.camera,camera_image:this.data.camera,camera_view:"live",show_name:false,show_state:false});
    this.cameraCard.hass=this._hass; this.el.camera.replaceChildren(this.cameraCard);
  }
  async mountPhone(){
    const device=this.el.phone.value;
    if(!device || this.mountedPhone===device)return;
    if(this.phoneCard){
      const current=this.data.phones.find(p=>p.device_id===this.mountedPhone);
      if(current && ["ringing","in_call","connecting","calling","remote_ringing"].includes(current.state)){
        this.el.phone.value=this.mountedPhone;throw new Error("Telefon displeje měň až po ukončení hovoru.");
      }
    }
    if(!customElements.get("voip-stack-card")){
      if(!this.data.module_url)throw new Error("Nejdřív otevři svůj stávající dashboard Intercom a vrať se sem. Karta VoIP ještě není načtená.");
      await import(this.data.module_url);
    }
    if(!this.isConnected)return;
    const card=document.createElement("voip-stack-card");
    card.setConfig({type:"custom:voip-stack-card",mode:"ha_softphone",device_id:device});
    card.hass=this._hass;this.el.call.replaceChildren(card);this.phoneCard=card;this.mountedPhone=device;
  }
}
if(!customElements.get("p4-doorbell-panel"))customElements.define("p4-doorbell-panel",P4DoorbellPanel);
