import { Bench } from '@/sections/Bench'
import { Hero } from '@/sections/Hero'
import { Results } from '@/sections/Results'
import { TokenStory } from '@/sections/TokenStory'

export default function App() {
  return (
    <div className="min-h-dvh bg-paper text-ink">
      <a href="#bench" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-brand focus:px-4 focus:py-2 focus:text-brand-ink">
        Skip to the bench
      </a>
      <Hero />
      <main>
        <TokenStory />
        <Results />
        <Bench />
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-baseline justify-between gap-3 px-5 py-8 text-xs text-muted sm:px-8">
          <p>IndicBridge · NLP project, RV University · every number read from the results files</p>
          <p>whisper-base + LoRA · MLX on Apple Silicon</p>
        </div>
      </footer>
    </div>
  )
}
