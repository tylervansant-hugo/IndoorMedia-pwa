<script>
  import { onMount } from 'svelte';

  let selectedChain = '';
  let allStores = [];
  let storeChains = [];
  let businessCardImage = null;
  let adProofImage = null;
  let selectedStyle = 'classic';
  let selectedSize = 'standard';
  let previewReady = false;

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

  onMount(async () => {
    try {
      const response = await fetch('/data/stores.json');
      allStores = await response.json();
      
      // Extract unique chains
      const chains = [...new Set(allStores.map(s => s.GroceryChain))].sort();
      storeChains = chains;
    } catch (err) {
      console.error('Failed to load stores:', err);
    }
  });

  function handleBusinessCardUpload(event) {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        businessCardImage = e.target?.result;
      };
      reader.readAsDataURL(file);
    }
  }

  function handleAdProofUpload(event) {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        adProofImage = e.target?.result;
      };
      reader.readAsDataURL(file);
    }
  }

  function getStyle() {
    return styles.find(s => s.id === selectedStyle) || styles[0];
  }

  function getSize() {
    return sizes.find(s => s.id === selectedSize) || sizes[1];
  }

  function downloadSign() {
    if (!selectedChain || !businessCardImage || !adProofImage) {
      alert('Please select store chain and upload both images');
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

    // Load and draw images
    const bcImg = new Image();
    const adImg = new Image();
    let imagesLoaded = 0;

    bcImg.onload = () => {
      imagesLoaded++;
      if (imagesLoaded === 2) drawComposite();
    };

    adImg.onload = () => {
      imagesLoaded++;
      if (imagesLoaded === 2) drawComposite();
    };

    bcImg.onerror = adImg.onerror = () => {
      alert('Error loading images');
    };

    bcImg.src = businessCardImage;
    adImg.src = adProofImage;

    function drawComposite() {
      // Draw ad proof (larger, centered)
      const adWidth = size.width - 60;
      const adHeight = size.height - 120;
      ctx.drawImage(adImg, 30, 30, adWidth, adHeight);

      // Store chain label
      ctx.fillStyle = style.color;
      ctx.font = `bold ${Math.round(size.width * 0.04)}px Arial`;
      ctx.textAlign = 'center';
      ctx.fillText(`Available at ${selectedChain}`, size.width / 2, size.height - 50);

      // Business card thumbnail (bottom corner)
      const bcThumbWidth = Math.round(size.width * 0.15);
      const bcThumbHeight = Math.round(bcThumbWidth * 0.6);
      ctx.drawImage(adImg, size.width - bcThumbWidth - 20, size.height - bcThumbHeight - 20, bcThumbWidth, bcThumbHeight);

      // Download
      canvas.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `counter-sign-${selectedChain}.png`;
        a.click();
        URL.revokeObjectURL(url);
      });
    }
  }

  $: previewReady = selectedChain && businessCardImage && adProofImage;
</script>

<div class="counter-sign-container">
  <h2>🏷️ Counter Sign Generator</h2>
  <p class="subtitle">Create in-store signage with IndoorMedia ad proof</p>

  <div class="form-section">
    <label>Select Store Chain Partner</label>
    <select bind:value={selectedChain}>
      <option value="">-- Choose a grocery chain --</option>
      {#each storeChains as chain}
        <option value={chain}>{chain}</option>
      {/each}
    </select>
  </div>

  <div class="form-section">
    <label>Business Card Image</label>
    <div class="upload-area">
      <input 
        type="file" 
        accept="image/*" 
        on:change={handleBusinessCardUpload}
        id="bc-upload"
      />
      <label for="bc-upload" class="upload-label">
        {businessCardImage ? '✅ Business card uploaded' : '📎 Click to upload business card image'}
      </label>
    </div>
  </div>

  <div class="form-section">
    <label>Ad Proof Image (from IndoorMedia Creative)</label>
    <div class="upload-area">
      <input 
        type="file" 
        accept="image/*" 
        on:change={handleAdProofUpload}
        id="ad-upload"
      />
      <label for="ad-upload" class="upload-label">
        {adProofImage ? '✅ Ad proof uploaded' : '📎 Click to upload ad proof image'}
      </label>
    </div>
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

  {#if previewReady}
    <div class="preview-section">
      <h3>Preview</h3>
      <div class="preview" style="background: {getStyle().bg}; width: {Math.min(getSize().width, 300)}px; aspect-ratio: {getSize().width / getSize().height};">
        <div class="preview-content">
          <img src={adProofImage} alt="Ad proof preview" />
          <span class="chain-label">{selectedChain}</span>
        </div>
      </div>
    </div>
  {/if}

  <button class="download-btn" on:click={downloadSign} disabled={!previewReady}>
    💾 Download Sign
  </button>
</div>

<style>
  .counter-sign-container { max-width: 600px; margin: 0 auto; }
  h2 { margin: 0 0 6px 0; font-size: 20px; }
  h3 { margin: 0 0 12px 0; font-size: 16px; }
  .subtitle { margin: 0 0 20px 0; font-size: 13px; color: #999; }

  .form-section { margin-bottom: 16px; }

  label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    margin-bottom: 6px;
  }

  select {
    width: 100%;
    padding: 10px 12px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
  }

  select:focus {
    outline: none;
    border-color: #CC0000;
  }

  .upload-area {
    position: relative;
    display: flex;
  }

  input[type="file"] {
    display: none;
  }

  .upload-label {
    flex: 1;
    padding: 14px 12px;
    background: white;
    border: 2px dashed #ddd;
    border-radius: 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 13px;
    font-weight: 500;
    color: #666;
  }

  .upload-label:hover {
    border-color: #CC0000;
    background: #fff5f5;
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
    padding: 12px;
    border: 4px solid currentColor;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    overflow: hidden;
  }

  .preview-content {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .preview-content img {
    max-width: 100%;
    max-height: 70%;
    object-fit: contain;
  }

  .chain-label {
    font-size: 11px;
    font-weight: 700;
    text-align: center;
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
