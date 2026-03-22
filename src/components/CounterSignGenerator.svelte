<script>
  let businessName = '';
  let offer = '';
  let phone = '';
  let selectedStyle = 'classic';
  let selectedSize = 'standard';

  const styles = [
    { id: 'classic', name: 'Classic', bg: '#CC0000', color: 'white' },
    { id: 'bold', name: 'Bold', bg: '#000', color: '#CC0000' },
    { id: 'soft', name: 'Soft', bg: '#FFF3E0', color: '#CC0000' },
    { id: 'modern', name: 'Modern', bg: '#333', color: 'white' }
  ];

  const sizes = [
    { id: 'small', name: 'Small (4x6")', width: 400, height: 300 },
    { id: 'standard', name: 'Standard (5x7")', width: 500, height: 350 },
    { id: 'large', name: 'Large (8x11")', width: 800, height: 550 }
  ];

  function getStyle() {
    return styles.find(s => s.id === selectedStyle) || styles[0];
  }

  function getSize() {
    return sizes.find(s => s.id === selectedSize) || sizes[1];
  }

  function downloadSign() {
    if (!businessName || !offer) {
      alert('Please enter business name and offer');
      return;
    }

    const size = getSize();
    const style = getStyle();

    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.width = size.width;
    canvas.height = size.height;
    const ctx = canvas.getContext('2d');

    // Fill background
    ctx.fillStyle = style.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw border
    ctx.strokeStyle = style.color;
    ctx.lineWidth = 4;
    ctx.strokeRect(10, 10, canvas.width - 20, canvas.height - 20);

    // Business name
    ctx.fillStyle = style.color;
    ctx.font = `bold ${Math.round(size.width * 0.08)}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(businessName.toUpperCase(), canvas.width / 2, 40);

    // Offer
    ctx.font = `${Math.round(size.width * 0.06)}px Arial`;
    ctx.fillStyle = style.color;
    wrapText(ctx, offer, canvas.width / 2, 120, canvas.width - 60, Math.round(size.width * 0.06));

    // Phone
    if (phone) {
      ctx.font = `bold ${Math.round(size.width * 0.05)}px Arial`;
      ctx.fillStyle = style.color;
      ctx.fillText(phone, canvas.width / 2, canvas.height - 60);
    }

    // Logo placeholder
    ctx.fillStyle = style.color;
    ctx.fillText('IndoorMedia', canvas.width / 2, canvas.height - 30);

    // Download
    canvas.toBlob(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${businessName}-counter-sign.png`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    const words = text.split(' ');
    let line = '';
    for (const word of words) {
      const test = line + word + ' ';
      const metrics = ctx.measureText(test);
      if (metrics.width > maxWidth && line.length > 0) {
        ctx.fillText(line, x, y);
        line = word + ' ';
        y += lineHeight;
      } else {
        line = test;
      }
    }
    ctx.fillText(line, x, y);
  }
</script>

<div class="counter-sign-container">
  <h2>🏷️ Counter Sign Generator</h2>
  <p class="subtitle">Create custom in-store signage</p>

  <div class="form-section">
    <label>Business Name</label>
    <input type="text" placeholder="e.g., Pedro's Taqueria" bind:value={businessName} />
  </div>

  <div class="form-section">
    <label>Offer / Message</label>
    <textarea placeholder="e.g., Save $5 on your next purchase with our register tape offer!" bind:value={offer} rows="3"></textarea>
  </div>

  <div class="form-section">
    <label>Phone Number (optional)</label>
    <input type="text" placeholder="(503) 555-0123" bind:value={phone} />
  </div>

  <div class="form-section">
    <label>Style</label>
    <div class="style-grid">
      {#each styles as style}
        <button
          class="style-btn"
          class:active={selectedStyle === style.id}
          on:click={() => selectedStyle = style.id}
          style="background: {style.bg}; color: {style.color}; border: {selectedStyle === style.id ? '3px solid #333' : '2px solid #ddd'}"
        >
          {style.name}
        </button>
      {/each}
    </div>
  </div>

  <div class="form-section">
    <label>Size</label>
    <div class="size-buttons">
      {#each sizes as size}
        <button
          class="size-btn {selectedSize === size.id ? 'active' : ''}"
          on:click={() => selectedSize = size.id}
        >
          {size.name}
        </button>
      {/each}
    </div>
  </div>

  {#if businessName && offer}
    <div class="preview-section">
      <h3>Preview</h3>
      <div class="preview" style="background: {getStyle().bg}; color: {getStyle().color}; width: {Math.min(getSize().width, 300)}px; aspect-ratio: {getSize().width / getSize().height};">
        <div class="preview-content">
          <h4>{businessName}</h4>
          <p>{offer}</p>
          {#if phone}
            <span class="preview-phone">{phone}</span>
          {/if}
        </div>
      </div>
    </div>
  {/if}

  <button class="download-btn" on:click={downloadSign} disabled={!businessName || !offer}>
    💾 Download Sign
  </button>
</div>

<style>
  .counter-sign-container { max-width: 600px; margin: 0 auto; }
  h2 { margin: 0 0 6px 0; font-size: 20px; }
  h3 { margin: 0 0 12px 0; font-size: 16px; }
  h4 { margin: 0 0 8px 0; font-size: 18px; font-weight: 700; }
  .subtitle { margin: 0 0 20px 0; font-size: 13px; color: #999; }

  .form-section { margin-bottom: 16px; }

  label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    margin-bottom: 6px;
  }

  input, textarea {
    width: 100%;
    padding: 10px 12px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
  }

  input:focus, textarea:focus {
    outline: none;
    border-color: #CC0000;
  }

  .style-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }

  .style-btn {
    padding: 12px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .style-btn.active { transform: scale(1.05); }

  .size-buttons {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .size-btn {
    padding: 12px;
    background: white;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .size-btn:hover { border-color: #CC0000; }
  .size-btn.active { background: #CC0000; color: white; border-color: #CC0000; }

  .preview-section {
    margin: 20px 0;
    padding: 16px;
    background: #f9f9f9;
    border-radius: 8px;
  }

  .preview {
    margin: 0 auto;
    padding: 20px;
    border: 4px solid currentColor;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .preview-content {
    text-align: center;
  }

  .preview-content p {
    margin: 8px 0;
    font-size: 12px;
    line-height: 1.4;
  }

  .preview-phone {
    display: block;
    margin-top: 8px;
    font-weight: 700;
    font-size: 14px;
  }

  .download-btn {
    width: 100%;
    padding: 14px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }

  .download-btn:hover { background: #990000; }
  .download-btn:disabled { background: #ccc; cursor: not-allowed; }

  @media (max-width: 480px) {
    .style-grid { grid-template-columns: repeat(2, 1fr); }
  }
</style>
