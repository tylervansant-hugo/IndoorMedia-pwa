import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

console.log('[main.js] Starting app mount...')

const target = document.getElementById('app')

if (!target) {
  console.error('[main.js] ERROR: No #app element found!')
} else {
  try {
    const app = mount(App, {
      target: target,
    })
    console.log('[main.js] ✅ App mounted!')
  } catch (err) {
    console.error('[main.js] ❌ Mount failed:', err)
    console.error('Stack:', err.stack)
  }
}

export default {}
