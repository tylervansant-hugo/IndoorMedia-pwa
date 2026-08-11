<script>
  // Reusable payment-details capture: Credit Card OR Bank (ACH) fields, plus a
  // "Capture Voided Check" button that opens the device camera. All values are
  // bound out via the `payment` object (two-way) + a change event.
  import { createEventDispatcher } from 'svelte';

  // payment = {
  //   method: 'card' | 'bank',
  //   card: { number, name, exp, cvv, zip },
  //   bank: { name, routing, account, accountType },
  //   voidedCheck: dataURL|null
  // }
  export let payment = {
    method: 'card',
    card: { number: '', name: '', exp: '', cvv: '', zip: '' },
    bank: { name: '', routing: '', account: '', accountType: 'Checking' },
    voidedCheck: null,
  };

  const dispatch = createEventDispatcher();
  let checkFileInput;

  function emit() { dispatch('change', payment); }

  function setMethod(m) { payment.method = m; payment = payment; emit(); }

  // Format card number in groups of 4 as they type.
  function onCardNumber(e) {
    let v = e.target.value.replace(/\D/g, '').slice(0, 19);
    payment.card.number = v.replace(/(.{4})/g, '$1 ').trim();
    payment = payment; emit();
  }
  function onExp(e) {
    let v = e.target.value.replace(/\D/g, '').slice(0, 4);
    if (v.length >= 3) v = v.slice(0, 2) + '/' + v.slice(2);
    payment.card.exp = v; payment = payment; emit();
  }

  function handleCheckPick(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      // Downscale to keep the data URL reasonable for the PDF.
      const img = new Image();
      img.onload = () => {
        const maxW = 1000;
        const scale = Math.min(1, maxW / img.width);
        const c = document.createElement('canvas');
        c.width = Math.round(img.width * scale);
        c.height = Math.round(img.height * scale);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        try { payment.voidedCheck = c.toDataURL('image/jpeg', 0.82); }
        catch { payment.voidedCheck = reader.result; }
        payment = payment; emit();
      };
      img.onerror = () => { payment.voidedCheck = reader.result; payment = payment; emit(); };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  }

  function clearCheck() { payment.voidedCheck = null; payment = payment; emit(); }
</script>

<div class="pay-wrap">
  <div class="pay-method-toggle">
    <button type="button" class="pm-btn" class:active={payment.method === 'card'} on:click={() => setMethod('card')}>💳 Credit / Debit Card</button>
    <button type="button" class="pm-btn" class:active={payment.method === 'bank'} on:click={() => setMethod('bank')}>🏦 Bank / ACH</button>
  </div>

  {#if payment.method === 'card'}
    <label class="pay-lbl">Cardholder Name
      <input bind:value={payment.card.name} on:input={emit} placeholder="Name on card" autocomplete="cc-name" />
    </label>
    <label class="pay-lbl">Card Number
      <input value={payment.card.number} on:input={onCardNumber} inputmode="numeric" placeholder="1234 5678 9012 3456" autocomplete="cc-number" />
    </label>
    <div class="pay-row">
      <label class="pay-lbl">Exp (MM/YY)
        <input value={payment.card.exp} on:input={onExp} inputmode="numeric" placeholder="MM/YY" autocomplete="cc-exp" />
      </label>
      <label class="pay-lbl pay-sm">CVV
        <input bind:value={payment.card.cvv} on:input={emit} inputmode="numeric" maxlength="4" placeholder="123" autocomplete="cc-csc" />
      </label>
      <label class="pay-lbl pay-sm">Billing Zip
        <input bind:value={payment.card.zip} on:input={emit} inputmode="numeric" placeholder="97201" />
      </label>
    </div>
  {:else}
    <label class="pay-lbl">Name on Account
      <input bind:value={payment.bank.name} on:input={emit} placeholder="Account holder name" />
    </label>
    <div class="pay-row">
      <label class="pay-lbl">Routing Number
        <input bind:value={payment.bank.routing} on:input={emit} inputmode="numeric" placeholder="9 digits" />
      </label>
      <label class="pay-lbl">Account Number
        <input bind:value={payment.bank.account} on:input={emit} inputmode="numeric" placeholder="Account #" />
      </label>
    </div>
    <label class="pay-lbl">Account Type
      <select bind:value={payment.bank.accountType} on:change={emit}>
        <option>Checking</option><option>Savings</option><option>Business Checking</option>
      </select>
    </label>
  {/if}

  <div class="void-check">
    {#if payment.voidedCheck}
      <div class="void-preview">
        <img src={payment.voidedCheck} alt="Voided check" />
        <button type="button" class="void-remove" on:click={clearCheck}>Remove</button>
      </div>
      <p class="void-ok">✓ Voided check captured</p>
    {:else}
      <button type="button" class="void-btn" on:click={() => checkFileInput.click()}>
        📷 Capture Voided Check
      </button>
      <p class="void-hint">Opens your camera to photograph a voided check (recommended for bank/ACH).</p>
    {/if}
    <input
      bind:this={checkFileInput}
      type="file"
      accept="image/*"
      capture="environment"
      on:change={handleCheckPick}
      hidden
    />
  </div>
</div>

<style>
  .pay-wrap { margin: 2px 0; }
  .pay-method-toggle { display: flex; gap: 8px; margin-bottom: 12px; }
  .pm-btn {
    flex: 1; padding: 11px 8px; border: 1.5px solid var(--border-color, #ddd);
    border-radius: 10px; background: var(--input-bg, #fff); color: var(--text-primary, #222);
    font-weight: 700; font-size: 13px; cursor: pointer; line-height: 1.2;
  }
  .pm-btn.active { border-color: var(--accent, #cc0000); background: rgba(204,0,0,0.08); color: var(--accent, #cc0000); }
  .pay-lbl { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary, #666); margin-bottom: 10px; }
  .pay-lbl input, .pay-lbl select {
    display: block; width: 100%; margin-top: 4px; padding: 10px 11px; box-sizing: border-box;
    border: 1px solid var(--border-color, #ddd); border-radius: 8px;
    background: var(--input-bg, #fff); color: var(--text-primary, #111);
    font-size: 15px; font-family: inherit;
  }
  .pay-row { display: flex; gap: 10px; }
  .pay-row > .pay-lbl { flex: 1; }
  .pay-row > .pay-lbl.pay-sm { flex: 0 0 92px; }
  .void-check { margin-top: 6px; }
  .void-btn {
    width: 100%; padding: 13px; border: 1.5px dashed var(--accent, #cc0000); border-radius: 10px;
    background: rgba(204,0,0,0.05); color: var(--accent, #cc0000);
    font-weight: 800; font-size: 14px; cursor: pointer;
  }
  .void-hint { font-size: 11px; color: var(--text-secondary, #888); text-align: center; margin: 6px 0 0; }
  .void-preview { position: relative; border: 1px solid var(--border-color, #ddd); border-radius: 10px; overflow: hidden; }
  .void-preview img { display: block; width: 100%; height: auto; }
  .void-remove {
    position: absolute; top: 8px; right: 8px; border: none; border-radius: 6px;
    background: rgba(0,0,0,0.65); color: #fff; font-weight: 700; font-size: 12px; padding: 6px 10px; cursor: pointer;
  }
  .void-ok { font-size: 12px; color: #0a7d29; font-weight: 700; text-align: center; margin: 6px 0 0; }
</style>
