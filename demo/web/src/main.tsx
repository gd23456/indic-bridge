import '@fontsource-variable/noto-sans-devanagari'
import '@fontsource-variable/noto-sans-kannada'
import '@fontsource-variable/noto-sans-oriya'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { initTheme } from './lib/theme'

initTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
