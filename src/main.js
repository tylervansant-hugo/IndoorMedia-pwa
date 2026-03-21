import { mount } from 'svelte'
import './app.css'
import Login from './components/Login.svelte'

console.log('[main.js] Starting app mount...')

const target = document.getElementById('app')
console.log('[main.js] Target element:', target)

if (!target) {
  console.error('[main.js] ERROR: No #app element found!')
} else {
  try {
    const app = mount(Login, {
      target: target,
    })
    console.log('[main.js] ✅ Login component mounted!')
  } catch (err) {
    console.error('[main.js] ❌ Mount failed:', err)
    console.error('Stack:', err.stack)
  }
}

export default {}
