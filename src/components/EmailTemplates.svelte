<script>
  let selectedTemplate = null;
  let businessName = '';
  let contactName = '';
  let repName = '';
  
  export let user;
  
  $: repName = user?.name || 'Your Rep';
  
  const templates = [
    {
      id: 'initial',
      icon: '🎯',
      name: 'Initial Appointment',
      subject: 'Quick question about {business}',
      body: `Hi {contact},

I noticed {business} in the area and wanted to reach out. We work with local businesses to help drive foot traffic through register tape advertising at nearby grocery stores.

Thousands of businesses like yours have seen measurable results — would you be open to a quick 10-minute chat this week?

Best,
{rep}
IndoorMedia`
    },
    {
      id: 'roi',
      icon: '📊',
      name: 'ROI / Value Focused',
      subject: 'How {business} can reach 10,000+ local customers',
      body: `Hi {contact},

Did you know the average grocery store gets 10,000+ visitors per week? That's 10,000 potential customers seeing your ad every single week.

Businesses in your category have reported strong ROI — many seeing results within the first month. Our register tape ads put your name, offer, and location directly in shoppers' hands.

I'd love to show you how the numbers work for {business}. Can we schedule a quick call?

Best,
{rep}
IndoorMedia`
    },
    {
      id: 'followup',
      icon: '⏰',
      name: 'Follow-up',
      subject: 'Following up — {business}',
      body: `Hi {contact},

Just following up on my earlier message. I know you're busy running {business}, so I'll keep this brief.

We have a few spots opening up at nearby stores and I wanted to make sure {business} gets first consideration. Would a 5-minute call work sometime this week?

Thanks,
{rep}
IndoorMedia`
    },
    {
      id: 'reengagement',
      icon: '🔄',
      name: 'Re-engagement',
      subject: 'Things have changed at IndoorMedia — {business}',
      body: `Hi {contact},

It's been a while since we last connected, and a lot has changed at IndoorMedia. We've expanded our store network and added new products that I think would be a great fit for {business}.

I'd love to reconnect and show you what's new. Are you available for a quick chat this week?

Best,
{rep}
IndoorMedia`
    },
    {
      id: 'limited',
      icon: '⚡',
      name: 'Limited Time Offer',
      subject: 'Limited availability — Partnership opportunity for {business}',
      body: `Hi {contact},

I'm reaching out because we have limited spots available in our partnership program at stores near {business}.

This is a unique opportunity to get your business in front of thousands of local shoppers every week at a fraction of the cost of other advertising.

Spots fill up fast — would you be interested in learning more before they're gone?

Best,
{rep}
IndoorMedia`
    }
  ];
  
  function selectTemplate(t) {
    selectedTemplate = t;
  }
  
  function getPreview(template) {
    return template.body
      .replace(/\{business\}/g, businessName || '[Business Name]')
      .replace(/\{contact\}/g, contactName || '[Contact Name]')
      .replace(/\{rep\}/g, repName);
  }
  
  function getSubjectPreview(template) {
    return template.subject
      .replace(/\{business\}/g, businessName || '[Business Name]');
  }
  
  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      alert('Copied to clipboard!');
    });
  }
</script>

<div class="email-container">
  <h2>✉️ Email Templates</h2>
  
  <div class="personalize">
    <input type="text" placeholder="Business name..." bind:value={businessName}>
    <input type="text" placeholder="Contact name..." bind:value={contactName}>
  </div>
  
  {#if !selectedTemplate}
    <div class="template-grid">
      {#each templates as t}
        <button class="template-card" on:click={() => selectTemplate(t)}>
          <span class="template-icon">{t.icon}</span>
          <span class="template-name">{t.name}</span>
        </button>
      {/each}
    </div>
  {:else}
    <div class="preview">
      <button class="back-btn" on:click={() => selectedTemplate = null}>← Back to Templates</button>
      
      <div class="email-preview">
        <div class="email-subject">
          <strong>Subject:</strong> {getSubjectPreview(selectedTemplate)}
        </div>
        <div class="email-body">
          {getPreview(selectedTemplate)}
        </div>
      </div>
      
      <div class="preview-actions">
        <button class="action-btn copy" on:click={() => copyToClipboard(getPreview(selectedTemplate))}>
          📋 Copy Email
        </button>
        <button class="action-btn copy" on:click={() => copyToClipboard(getSubjectPreview(selectedTemplate))}>
          📋 Copy Subject
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .email-container { max-width: 700px; margin: 0 auto; }
  h2 { margin: 0 0 16px 0; font-size: 20px; }
  
  .personalize {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }
  
  .personalize input {
    flex: 1;
    padding: 10px 14px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
  }
  
  .personalize input:focus {
    outline: none;
    border-color: #CC0000;
  }
  
  .template-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .template-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 20px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    transition: all 0.2s;
  }
  
  .template-card:hover {
    border-color: #CC0000;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }
  
  .template-icon { font-size: 28px; }
  .template-name { font-size: 14px; font-weight: 600; color: #333; text-align: center; }
  
  .back-btn {
    background: none;
    border: none;
    color: #CC0000;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    margin-bottom: 12px;
  }
  
  .email-preview {
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  .email-subject {
    padding: 14px 16px;
    background: #f8f8f8;
    border-bottom: 1px solid #e0e0e0;
    font-size: 14px;
  }
  
  .email-body {
    padding: 20px;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    color: #333;
  }
  
  .preview-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  
  .action-btn {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .action-btn.copy {
    background: #CC0000;
    color: white;
  }
  
  .action-btn.copy:hover { background: #990000; }
  
  @media (max-width: 480px) {
    .template-grid { grid-template-columns: 1fr; }
    .personalize { flex-direction: column; }
    .preview-actions { flex-direction: column; }
  }
</style>
