<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { getShortcuts, removeShortcut, reorderShortcuts } from '../lib/homeShortcuts.js';

  const dispatch = createEventDispatcher();

  let shortcuts = getShortcuts();
  let editMode = false;
  let dragIdx = null;
  let overIdx = null;

  function refresh() { shortcuts = getShortcuts(); }
  const onChanged = () => refresh();

  onMount(() => { window.addEventListener('home-shortcuts-changed', onChanged); });
  onDestroy(() => { window.removeEventListener('home-shortcuts-changed', onChanged); });

  function open(sc) {
    if (editMode) return;
    // Pass the whole shortcut (incl. matchText) so Main can re-click the real button.
    dispatch('navigate', { ...sc, shortcut: sc });
  }
  function remove(id) { shortcuts = removeShortcut(id); }

  // Drag reorder (HTML5 DnD for desktop; touch handled via long-press move).
  function onDragStart(i) { dragIdx = i; }
  function onDragOver(i, e) { e.preventDefault(); overIdx = i; }
  function onDrop(i) {
    if (dragIdx !== null && dragIdx !== i) shortcuts = reorderShortcuts(dragIdx, i);
    dragIdx = null; overIdx = null;
  }
</script>

{#if shortcuts.length > 0 || editMode}
  <div class="hs-widget">
    <div class="hs-head">
      <span class="hs-title">⭐ Home Shortcuts</span>
      <button class="hs-edit" on:click={() => editMode = !editMode}>{editMode ? 'Done' : 'Edit'}</button>
    </div>

    {#if shortcuts.length === 0}
      <p class="hs-empty">Long-press any button (Find Prospects, Tools, etc.) and tap “Add to Home Screen” to pin it here.</p>
    {:else}
      <div class="hs-grid">
        {#each shortcuts as sc, i (sc.id)}
          <div
            class="hs-item"
            class:editing={editMode}
            class:dragover={overIdx === i}
            draggable={editMode}
            on:dragstart={() => onDragStart(i)}
            on:dragover={(e) => onDragOver(i, e)}
            on:drop={() => onDrop(i)}
            on:click={() => open(sc)}
          >
            {#if editMode}
              <button class="hs-remove" on:click|stopPropagation={() => remove(sc.id)} aria-label="Remove">✕</button>
            {/if}
            <span class="hs-icon">{sc.icon}</span>
            <span class="hs-label">{sc.label}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .hs-widget {
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 16px;
    padding: 14px 16px 16px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px var(--card-shadow, rgba(0,0,0,0.06));
  }
  .hs-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .hs-title { font-weight: 800; font-size: 15px; color: var(--text-primary, #1a1a1a); }
  .hs-edit {
    border: 1px solid var(--border-color, #ddd); background: transparent;
    color: var(--accent, #cc0000); font-weight: 700; font-size: 13px;
    padding: 4px 12px; border-radius: 8px; cursor: pointer;
  }
  .hs-empty { font-size: 13px; color: var(--text-secondary, #888); margin: 0; line-height: 1.5; }
  .hs-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .hs-item {
    position: relative; display: flex; flex-direction: column; align-items: center;
    gap: 6px; padding: 12px 6px; border-radius: 14px; cursor: pointer;
    background: var(--bg-secondary, #f6f6f8); border: 1px solid transparent;
    transition: transform .1s, border-color .15s;
    user-select: none;
  }
  .hs-item:active { transform: scale(0.95); }
  .hs-item.dragover { border-color: var(--accent, #cc0000); }
  .hs-item.editing { animation: hs-wiggle 0.4s infinite alternate ease-in-out; }
  @keyframes hs-wiggle { from { transform: rotate(-1.3deg); } to { transform: rotate(1.3deg); } }
  .hs-icon { font-size: 26px; line-height: 1; }
  .hs-label { font-size: 11px; font-weight: 600; color: var(--text-primary, #333); text-align: center; line-height: 1.2; max-width: 100%; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
  .hs-remove {
    position: absolute; top: -6px; left: -6px; width: 22px; height: 22px;
    border-radius: 50%; border: none; background: #cc0000; color: #fff;
    font-size: 12px; font-weight: 900; cursor: pointer; z-index: 2; line-height: 1;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }
  @media (max-width: 380px) { .hs-grid { grid-template-columns: repeat(3, 1fr); } }
</style>
