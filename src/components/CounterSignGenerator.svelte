<script>
  import { onMount } from 'svelte';

  let selectedChain = '';
  let allStores = [];
  let storeChains = [];
  let businessCardImage = null;
  let adProofImage = null;
  let landingPageUrl = '';
  let selectedSize = 'standard';

  const sizes = [
    { id: 'small', name: 'Small (4x6")', label: '4x6' },
    { id: 'standard', name: 'Standard (5x7")', label: '5x7' },
    { id: 'large', name: 'Large (8.5x11")', label: '8.5x11' }
  ];

  onMount(async () => {
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
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

  function getSize() {
    return sizes.find(s => s.id === selectedSize) || sizes[1];
  }

  async function downloadSign() {
    if (!selectedChain || !businessCardImage || !adProofImage || !landingPageUrl) {
      alert('Please fill in all fields:');
      if (!selectedChain) alert('- Select store chain');
      if (!businessCardImage) alert('- Upload business card');
      if (!adProofImage) alert('- Upload ad proof');
      if (!landingPageUrl) alert('- Enter landing page URL');
      return;
    }

    // Validate URL
    if (!landingPageUrl.startsWith('http')) {
      alert('Please enter a valid URL (starting with http:// or https://)');
      return;
    }

    // We'll create the sign using canvas and QR code
    // Import needed libraries
    const { QRCodeCanvas } = window;

    // Create main canvas
    const size = getSize();
    let canvasWidth, canvasHeight;
    
    if (size.id === 'small') {
      canvasWidth = 400;
      canvasHeight = 300;
    } else if (size.id === 'standard') {
      canvasWidth = 500;
      canvasHeight = 350;
    } else {
      canvasWidth = 850;
      canvasHeight = 1100;
    }

    const canvas = document.createElement('canvas');
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    const ctx = canvas.getContext('2d');

    // White background
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Border
    ctx.strokeStyle = '#CC0000';
    ctx.lineWidth = 4;
    ctx.strokeRect(10, 10, canvasWidth - 20, canvasHeight - 20);

    // Load images
    const bcImg = new Image();
    const adImg = new Image();
    let loaded = 0;

    const onLoad = () => {
      loaded++;
      if (loaded === 2) composeSign();
    };

    bcImg.onload = onLoad;
    adImg.onload = onLoad;
    bcImg.onerror = adImg.onerror = () => alert('Error loading images');

    bcImg.src = businessCardImage;
    adImg.src = adProofImage;

    function composeSign() {
      // Draw ad proof (main content area)
      const adMargin = 20;
      const adWidth = canvasWidth - (2 * adMargin);
      const footerHeight = canvasHeight * 0.15;
      const adHeight = canvasHeight - (2 * adMargin) - footerHeight;
      
      ctx.drawImage(adImg, adMargin, adMargin, adWidth, adHeight);

      // Footer area
      const footerY = adMargin + adHeight;
      
      // Background for footer
      ctx.fillStyle = '#f5f5f5';
      ctx.fillRect(adMargin, footerY, adWidth, footerHeight);
      
      // Business card (left side)
      const bcSize = Math.min(footerHeight - 10, adWidth * 0.2);
      ctx.drawImage(bcImg, adMargin + 5, footerY + (footerHeight - bcSize) / 2, bcSize, bcSize);

      // QR Code (right side)
      try {
        const qrCanvas = document.createElement('canvas');
        const qr = new QRCode({
          content: landingPageUrl,
          width: 100,
          height: 100,
          colorLight: '#ffffff',
          colorDark: '#000000'
        });
        qr.canvas.toBlob(blob => {
          const qrImg = new Image();
          const qrSize = Math.min(footerHeight - 10, adWidth * 0.15);
          qrImg.onload = () => {
            ctx.drawImage(qrImg, canvasWidth - adMargin - qrSize - 5, footerY + (footerHeight - qrSize) / 2, qrSize, qrSize);
            
            // Store chain text
            ctx.fillStyle = '#333';
            ctx.font = `bold ${Math.round(canvasWidth * 0.04)}px Arial`;
            ctx.textAlign = 'center';
            ctx.fillText(`Now Available at ${selectedChain}`, canvasWidth / 2, canvasHeight - 8);
            
            // Download
            downloadCanvas(canvas);
          };
          qrImg.src = URL.createObjectURL(blob);
        });
      } catch (e) {
        console.log('QR code lib not available, creating without QR');
        // Fallback: just text for QR
        ctx.fillStyle = '#CC0000';
        ctx.font = `bold ${Math.round(canvasWidth * 0.04)}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(`Scan for more info`, canvasWidth - adMargin - 50, footerY + footerHeight / 2);
        
        ctx.fillStyle = '#333';
        ctx.fillText(`Now Available at ${selectedChain}`, canvasWidth / 2, canvasHeight - 8);
        
        downloadCanvas(canvas);
      }
    }

    function downloadCanvas(c) {
      c.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedChain}-counter-sign-${size.label}.png`;
        a.click();
        URL.revokeObjectURL(url);
      });
    }
  }

  $: isReady = selectedChain && businessCardImage && adProofImage && landingPageUrl;
</script>

<div class="counter-sign-container">
  <h2>🏷️ Counter Sign Generator</h2>
  <p class="subtitle">Create in-store signage with QR code</p>

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
        {businessCardImage ? '✅ Business card uploaded' : '📎 Click to upload business card'}
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
        {adProofImage ? '✅ Ad proof uploaded' : '📎 Click to upload ad proof'}
      </label>
    </div>
  </div>

  <div class="form-section">
    <label>Landing Page URL (for QR code)</label>
    <input 
      type="url" 
      placeholder="https://your-landing-page.com" 
      bind:value={landingPageUrl}
    />
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

  {#if isReady}
    <div class="preview-section">
      <h3>Preview</h3>
      <div class="preview-info">
        <span>📍 {selectedChain}</span>
        <span>📏 {getSize().label}</span>
        <span>🔗 QR Code Enabled</span>
      </div>
    </div>
  {/if}

  <button class="download-btn" on:click={downloadSign} disabled={!isReady}>
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

  select, input[type="url"] {
    width: 100%;
    padding: 10px 12px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
  }

  select:focus, input[type="url"]:focus {
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

  .preview-info {
    display: flex;
    justify-content: space-around;
    gap: 12px;
    font-size: 13px;
    font-weight: 600;
    color: #333;
  }

  .preview-info span {
    padding: 8px 12px;
    background: white;
    border-radius: 6px;
    border: 1px solid #ddd;
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
    .preview-info { flex-direction: column; }
  }
</style>
