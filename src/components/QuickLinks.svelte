<script>
  const links = [
    { icon: '🗺️', name: 'MapPoint', url: 'https://sales.indoormedia.com/Mappoint', desc: 'Territory mapping' },
    { icon: '🎟️', name: 'Coupons', url: 'https://coupons.indoormedia.com', desc: 'Coupon portal' },
    { icon: '📁', name: 'Google Drive', url: 'https://drive.google.com/drive', desc: 'Team files' },
    { icon: '🌐', name: 'IndoorMedia.com', url: 'https://indoormedia.com', desc: 'Company website' },
    { icon: '📊', name: 'Sales Portal', url: 'https://sales.indoormedia.com', desc: 'Sales dashboard' },
    { icon: '💬', name: 'Testimonials', url: 'https://testimonials.indoormedia.com', desc: 'Customer reviews' },
  ];
</script>

<div class="links-container">
  <h2>🔗 Quick Links</h2>
  
  <div class="links-grid">
    {#each links as link}
      <a href={link.url} target="_blank" rel="noopener" class="link-card">
        <span class="link-icon">{link.icon}</span>
        <div class="link-info">
          <span class="link-name">{link.name}</span>
          <span class="link-desc">{link.desc}</span>
        </div>
        <span class="link-arrow">→</span>
      </a>
    {/each}
  </div>
</div>

<style>
  .links-container { max-width: 600px; margin: 0 auto; }
  h2 { margin: 0 0 16px 0; font-size: 20px; }
  
  .links-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .link-card {
    display: flex;
    align-items: center;
    gap: 14px;
    background: white;
    padding: 16px;
    border-radius: 10px;
    text-decoration: none;
    color: inherit;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    transition: all 0.2s;
  }
  
  .link-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  }
  
  .link-icon { font-size: 28px; }
  .link-info { flex: 1; }
  .link-name { display: block; font-weight: 600; font-size: 15px; color: #1a1a1a; }
  .link-desc { display: block; font-size: 12px; color: #999; margin-top: 2px; }
  .link-arrow { font-size: 18px; color: #ccc; }
</style>
