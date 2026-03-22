<script>
  import { onMount } from 'svelte';
  
  let notes = '';
  let saved = false;
  
  onMount(() => {
    notes = localStorage.getItem('notepad') || '';
  });
  
  function save() {
    localStorage.setItem('notepad', notes);
    saved = true;
    setTimeout(() => saved = false, 2000);
  }
  
  function clear() {
    if (confirm('Clear notepad?')) {
      notes = '';
      localStorage.setItem('notepad', '');
    }
  }
</script>

<div class="notepad-container">
  <h2>📝 Notepad</h2>
  <p class="subtitle">Quick notes for the field</p>
  
  <textarea
    bind:value={notes}
    placeholder="Jot down notes, reminders, store observations..."
    rows="12"
  ></textarea>
  
  <div class="actions">
    <button class="save-btn" on:click={save}>
      {saved ? '✅ Saved!' : '💾 Save'}
    </button>
    <button class="clear-btn" on:click={clear}>🗑️ Clear</button>
  </div>
</div>

<style>
  .notepad-container { max-width: 600px; margin: 0 auto; }
  h2 { margin: 0; font-size: 20px; }
  .subtitle { color: #666; font-size: 14px; margin: 4px 0 16px 0; }
  
  textarea {
    width: 100%;
    padding: 16px;
    border: 2px solid #ddd;
    border-radius: 10px;
    font-size: 15px;
    font-family: inherit;
    line-height: 1.5;
    resize: vertical;
  }
  
  textarea:focus { outline: none; border-color: #CC0000; }
  
  .actions { display: flex; gap: 8px; margin-top: 12px; }
  
  .save-btn {
    flex: 3;
    padding: 12px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
  }
  
  .save-btn:hover { background: #990000; }
  
  .clear-btn {
    flex: 1;
    padding: 12px;
    background: #f0f0f0;
    color: #666;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    cursor: pointer;
  }
  
  .clear-btn:hover { background: #e0e0e0; }
</style>
