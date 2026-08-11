<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import { generateContractPdf, nextContractNumber } from '../lib/contractGenerator.js';
  import SignaturePad from './SignaturePad.svelte';
  import PaymentDetails from './PaymentDetails.svelte';

  // Optional seed data from a store card or a prospect "Add Product" flow.
  export let store = null;      // { StoreName, GroceryChain, Address, City, State, PostalCode, Cycle, zone... }
  export let prospect = null;   // { business_name, contact_name, email, phone, address... }
  export let seedItem = null;   // single { product, price, adType, quarters, ... }
  export let seedItems = null;  // array of line items (e.g. from the quote/cart)

  const dispatch = createEventDispatcher();

  // ── Product catalog for the "add product" dropdown ──
  const PRODUCT_OPTIONS = [
    'Register Tape', 'Cartvertising', 'Nose of Cart', 'DigitalBoost',
    'FindLocal', 'ReviewBoost', 'LoyaltyBoost',
  ];
  const AD_TYPES = ['Single Ad', 'Double Ad'];

  // Padded (full-rate) default prices per product + ad type. The lower/unlocked
  // price is revealed only after a rep types ANY unlock code.
  const PADDED_PRICE = {
    'Register Tape': { 'Single Ad': 4050, 'Double Ad': 5670 },
    'Cartvertising': { 'Single Ad': 2995, 'Double Ad': 4795 },
    'Nose of Cart':  { 'Single Ad': 2500, 'Double Ad': 3995 },
    'DigitalBoost':  { 'Single Ad': 3600, 'Double Ad': 7200 },
    'FindLocal':     { 'Single Ad': 695,  'Double Ad': 1390 },
    'ReviewBoost':   { 'Single Ad': 695,  'Double Ad': 1390 },
    'LoyaltyBoost':  { 'Single Ad': 3600, 'Double Ad': 7200 },
  };
  function paddedPrice(product, adType) { return (PADDED_PRICE[product]?.[adType]) ?? ''; }
  function unlockedPrice(product, adType) {
    const p = PADDED_PRICE[product]?.[adType];
    return p != null ? Math.max(0, p - 1200) : '';
  }

  // Global unlock: ANY non-empty code unlocks lower pricing for all items.
  let unlockCode = '';
  let priceUnlocked = false;
  function applyUnlock() {
    const was = priceUnlocked;
    priceUnlocked = unlockCode.trim().length > 0;
    if (priceUnlocked !== was) {
      items = items.map(it => it._autoPrice
        ? { ...it, price: priceUnlocked ? unlockedPrice(it.product, it.adType) : paddedPrice(it.product, it.adType) }
        : it);
    }
  }
  function onProductChange(i) {
    const it = items[i];
    if (it._autoPrice) {
      it.price = priceUnlocked ? unlockedPrice(it.product, it.adType) : paddedPrice(it.product, it.adType);
    }
    items = items;
  }
  function onManualPrice(i) { items[i]._autoPrice = false; items = items; }

  // Payment + signature state
  let payment = {
    method: 'card',
    card: { number: '', name: '', exp: '', cvv: '', zip: '' },
    bank: { name: '', routing: '', account: '', accountType: 'Checking' },
    voidedCheck: null,
  };
  let signerName = prospect?.contact_name || prospect?.contact || '';
  let signatureImage = '';

  let contractNumber = 'Loading…';
  let generating = false;
  let genError = '';

  // Form fields
  let businessName = prospect?.business_name || prospect?.name || '';
  let contactName = prospect?.contact_name || prospect?.contact || '';
  let contactEmail = prospect?.email || prospect?.contact_email || '';
  let contactPhone = prospect?.phone || prospect?.contact_phone || '';
  let billingAddress = prospect?.address || store?.Address || '';
  let city = prospect?.city || store?.City || '';
  let state = prospect?.state || store?.State || '';
  let zip = prospect?.zip || store?.PostalCode || '';
  let isNewCustomer = true;
  let digitalIntegration = false;
  let paymentFrequency = 'monthly';
  let termMonths = 12;
  let depositAmount = '';
  let firstPaymentDate = new Date().toISOString().slice(0, 10);
  let salesTax = 0;
  let initials = '';

  // Line items. Defaults to the store the customer was looked up at.
  function newItem() {
    const product = 'Register Tape';
    const adType = 'Single Ad';
    return {
      product,
      storeName: store?.GroceryChain || store?.StoreName || '',
      storeNumber: store?.StoreName || store?.StoreNumber || '',
      zone: store?.zone || store?.Cycle || store?.ZoneName || '',
      address: store?.Address ? `${store.Address}, ${store.City || ''} ${store.PostalCode || ''}`.trim() : '',
      startInfo: '',
      adType,
      quarters: 4,
      price: paddedPrice(product, adType),
      _autoPrice: true,
    };
  }
  let items = (Array.isArray(seedItems) && seedItems.length)
    ? seedItems.map(si => ({ ...newItem(), ...si, _autoPrice: si.price == null }))
    : [ seedItem ? { ...newItem(), ...seedItem, _autoPrice: seedItem.price == null } : newItem() ];

  function addItem() { items = [...items, newItem()]; }
  function removeItem(i) { items = items.filter((_, idx) => idx !== i); }

  $: net = items.reduce((s, it) => s + (parseFloat(it.price) || 0), 0);
  $: grandTotal = net + (parseFloat(salesTax) || 0);

  onMount(async () => {
    // Load existing contract numbers to compute the next IMPRO number.
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now());
      const raw = await res.json();
      const arr = Array.isArray(raw) ? raw : Object.values(raw);
      const nums = arr.map(c => c.contract_number).filter(Boolean);
      contractNumber = nextContractNumber(nums);
    } catch {
      contractNumber = nextContractNumber([]);
    }
  });

  function close() { dispatch('close'); }

  async function generate() {
    if (generating) return;
    genError = '';
    if (!businessName.trim()) { genError = 'Business name is required.'; return; }
    if (!items.length) { genError = 'Add at least one product.'; return; }
    generating = true;
    try {
      const { blob, bytes, filename } = await generateContractPdf({
        contractNumber,
        businessName, contactName, contactEmail, contactPhone,
        billingAddress, city, state, zip,
        repName: $user?.name || $user?.display_name || $user?.first_name || '',
        repEmail: $user?.email || '',
        repPhone: $user?.phone || $user?.cell || '',
        isNewCustomer, digitalIntegration,
        billingType: payment.method === 'bank' ? 'ACH / Bank' : 'Credit Card',
        paymentFrequency,
        termMonths: parseInt(termMonths) || 12,
        depositAmount: depositAmount === '' ? null : parseFloat(depositAmount),
        firstPaymentDate,
        salesTax: parseFloat(salesTax) || 0,
        initials,
        signerName,
        signatureImage,
        signature: signerName,
        signedDate: signatureImage ? new Date().toLocaleDateString() : '',
        paymentDetails: payment,
        items: items.map(it => ({
          product: it.product,
          storeName: it.storeName,
          storeNumber: it.storeNumber,
          zone: it.zone,
          address: it.address,
          startInfo: it.startInfo,
          adType: it.adType,
          quarters: parseInt(it.quarters) || undefined,
          price: parseFloat(it.price) || 0,
        })),
      });

      if (navigator.share && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
        try {
          await navigator.share({ files: [new File([bytes], filename, { type: 'application/pdf' })], title: filename });
          generating = false;
          return;
        } catch { /* fall through to open */ }
      }
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (e) {
      genError = 'Could not generate contract: ' + (e?.message || e);
      console.error(e);
    } finally {
      generating = false;
    }
  }
</script>

<div class="cf-overlay" on:click|self={close}>
  <div class="cf-modal">
    <button class="cf-close" on:click={close} aria-label="Close">✕</button>
    <h2>📄 New Customer Contract</h2>
    <p class="cf-sub">Contract #: <strong>{contractNumber}</strong></p>

    <fieldset>
      <legend>Customer</legend>
      <label>Business Name *<input bind:value={businessName} /></label>
      <label>Contact Name<input bind:value={contactName} /></label>
      <div class="cf-row">
        <label>Email<input type="email" bind:value={contactEmail} /></label>
        <label>Phone<input bind:value={contactPhone} /></label>
      </div>
      <label>Address<input bind:value={billingAddress} /></label>
      <div class="cf-row">
        <label>City<input bind:value={city} /></label>
        <label class="cf-sm">State<input bind:value={state} /></label>
        <label class="cf-sm">Zip<input bind:value={zip} /></label>
      </div>
      <div class="cf-checks">
        <label class="cf-check"><input type="checkbox" bind:checked={isNewCustomer} /> New Customer</label>
        <label class="cf-check"><input type="checkbox" bind:checked={digitalIntegration} /> Digital Integration</label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Products</legend>
      {#if store}<p class="cf-store-note">📍 Defaulting to <strong>{store.GroceryChain || store.StoreName}{store.StoreName && store.GroceryChain ? ' — ' + store.StoreName : ''}</strong> (the store you looked them up at)</p>{/if}
      {#each items as it, i}
        <div class="cf-item">
          <div class="cf-item-head">
            <span>Item {i + 1}</span>
            {#if items.length > 1}<button class="cf-item-remove" on:click={() => removeItem(i)}>Remove</button>{/if}
          </div>
          <div class="cf-row">
            <label>Product
              <select bind:value={it.product} on:change={() => onProductChange(i)}>
                {#each PRODUCT_OPTIONS as p}<option>{p}</option>{/each}
              </select>
            </label>
            <label class="cf-sm">Ad
              <select bind:value={it.adType} on:change={() => onProductChange(i)}>
                {#each AD_TYPES as a}<option>{a}</option>{/each}
              </select>
            </label>
          </div>
          <div class="cf-row">
            <label>Price $
              <input type="number" bind:value={it.price} on:input={() => onManualPrice(i)} placeholder="0.00" />
            </label>
            <label class="cf-sm">Quarters<input type="number" bind:value={it.quarters} min="1" max="4" /></label>
          </div>
          {#if it._autoPrice}
            <p class="cf-price-tag">{priceUnlocked ? '🔓 Unlocked price applied' : '💲 Full rate (padded)'} — ${(Number(it.price)||0).toLocaleString()}</p>
          {/if}
          <div class="cf-row">
            <label>Store / Chain<input bind:value={it.storeName} /></label>
            <label class="cf-sm">Store #<input bind:value={it.storeNumber} /></label>
            <label class="cf-sm">Zone<input bind:value={it.zone} /></label>
          </div>
          <label>Store Address<input bind:value={it.address} /></label>
          <label>Est. Start<input bind:value={it.startInfo} placeholder="C2 06/17/2025" /></label>
        </div>
      {/each}
      <button class="cf-add" on:click={addItem}>＋ Add another product</button>

      <div class="cf-unlock">
        <label>🔓 Unlock lower pricing (enter code)
          <input bind:value={unlockCode} on:input={applyUnlock} placeholder="Enter code to unlock" />
        </label>
        {#if priceUnlocked}<span class="cf-unlock-ok">✓ Lower pricing unlocked</span>{/if}
      </div>
    </fieldset>

    <fieldset>
      <legend>Payment</legend>
      <PaymentDetails bind:payment />
      <div class="cf-row" style="margin-top:12px">
        <label>Frequency
          <select bind:value={paymentFrequency}>
            <option>monthly</option><option>quarterly</option><option>annually</option><option>paid in full</option>
          </select>
        </label>
        <label class="cf-sm">Term (mo)<input type="number" bind:value={termMonths} min="1" max="48" /></label>
      </div>
      <div class="cf-row">
        <label>Deposit $<input type="number" bind:value={depositAmount} placeholder="auto" /></label>
        <label>First Payment<input type="date" bind:value={firstPaymentDate} /></label>
        <label class="cf-sm">Sales Tax $<input type="number" bind:value={salesTax} /></label>
      </div>
      <div class="cf-totals">
        <span>Net: <strong>${net.toLocaleString(undefined,{minimumFractionDigits:2})}</strong></span>
        <span>Total: <strong>${grandTotal.toLocaleString(undefined,{minimumFractionDigits:2})}</strong></span>
      </div>
    </fieldset>

    <fieldset>
      <legend>E-Signature</legend>
      <SignaturePad
        bind:name={signerName}
        bind:signatureData={signatureImage}
        nameLabel="Customer's Full Name"
        label="Customer Signature" />
    </fieldset>

    {#if genError}<div class="cf-err">{genError}</div>{/if}

    <button class="cf-generate" on:click={generate} disabled={generating}>
      {generating ? 'Generating…' : '📄 Generate Contract PDF'}
    </button>
    <p class="cf-note">Terms & Conditions pages are included automatically, exactly as on current contracts.</p>
  </div>
</div>

<style>
  .cf-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.55);
    display: flex; align-items: flex-start; justify-content: center;
    z-index: 1200; padding: 18px 10px; overflow-y: auto;
  }
  .cf-modal {
    position: relative; background: var(--card-bg, #fff); color: var(--text-primary, #111);
    border-radius: 16px; width: 100%; max-width: 560px; padding: 22px 18px 26px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.3); margin: auto 0;
  }
  .cf-close {
    position: absolute; top: 12px; right: 12px; width: 34px; height: 34px;
    border: none; border-radius: 50%; background: var(--border-color, #eee);
    color: var(--text-primary, #333); font-size: 16px; cursor: pointer; line-height: 1;
  }
  h2 { margin: 0 0 2px; font-size: 20px; }
  .cf-sub { margin: 0 0 14px; font-size: 13px; color: var(--text-secondary, #777); }
  .cf-sub strong { color: var(--accent, #cc0000); }
  fieldset {
    border: 1px solid var(--border-color, #e2e2e2); border-radius: 12px;
    padding: 12px 12px 14px; margin: 0 0 14px;
  }
  legend { font-weight: 800; font-size: 13px; padding: 0 6px; color: var(--text-primary, #222); }
  label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary, #666); margin-bottom: 10px; }
  input, select {
    display: block; width: 100%; margin-top: 4px; padding: 9px 10px; box-sizing: border-box;
    border: 1px solid var(--border-color, #ddd); border-radius: 8px;
    background: var(--input-bg, #fff); color: var(--text-primary, #111);
    font-size: 14px; font-family: inherit;
  }
  .cf-row { display: flex; gap: 10px; }
  .cf-row > label { flex: 1; }
  .cf-row > label.cf-sm { flex: 0 0 90px; }
  .cf-checks { display: flex; gap: 18px; }
  .cf-check { display: flex; align-items: center; gap: 6px; }
  .cf-check input { width: auto; margin: 0; }
  .cf-item { border: 1px dashed var(--border-color, #ddd); border-radius: 10px; padding: 10px; margin-bottom: 10px; }
  .cf-item-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; font-size: 12px; margin-bottom: 8px; }
  .cf-item-remove { border: none; background: transparent; color: #cc0000; font-weight: 700; font-size: 12px; cursor: pointer; }
  .cf-add {
    width: 100%; padding: 10px; border: 1px dashed var(--accent, #cc0000); border-radius: 9px;
    background: transparent; color: var(--accent, #cc0000); font-weight: 700; font-size: 13px; cursor: pointer;
  }
  .cf-totals { display: flex; gap: 20px; font-size: 14px; margin-top: 4px; }
  .cf-err { background: rgba(204,0,0,0.1); color: #cc0000; padding: 10px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 12px; }
  .cf-generate {
    width: 100%; padding: 14px; border: none; border-radius: 10px;
    background: var(--accent, #cc0000); color: #fff; font-weight: 800; font-size: 15px; cursor: pointer;
  }
  .cf-generate:disabled { opacity: 0.6; cursor: not-allowed; }
  .cf-note { font-size: 11px; color: var(--text-secondary, #888); text-align: center; margin: 10px 0 0; }
  .cf-store-note {
    font-size: 12px; color: var(--text-secondary, #555); margin: 0 0 10px;
    background: rgba(204,0,0,0.06); padding: 8px 10px; border-radius: 8px;
  }
  .cf-store-note strong { color: var(--accent, #cc0000); }
  .cf-price-tag { font-size: 11px; color: var(--text-secondary, #777); margin: -4px 0 8px; font-weight: 600; }
  .cf-unlock { margin-top: 6px; display: flex; align-items: flex-end; gap: 10px; }
  .cf-unlock > label { flex: 1; margin-bottom: 0; }
  .cf-unlock-ok { font-size: 12px; font-weight: 700; color: #0a7d29; padding-bottom: 10px; white-space: nowrap; }
</style>
