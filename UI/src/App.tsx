import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function App() {
  return (
    <div className="min-h-screen bg-bg text-ink p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="border-b border-line pb-4">
          <h1 className="text-4xl font-display text-accent">Antigravity UI Scaffold</h1>
          <p className="text-ink-dim mt-2">React 19 + Tailwind CSS 4 + shadcn/ui v4</p>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-bg-elev border-line border-l-4 border-l-accent shadow-none">
            <CardHeader>
              <CardTitle className="text-ink text-sm uppercase tracking-widest text-ink-soft">System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-mono font-bold text-ink">1.24 <span className="text-xs font-normal text-ink-dim">CCI</span></div>
              <p className="text-alert-warning text-xs mt-1 font-mono">WARNING: LEVEL 2</p>
            </CardContent>
          </Card>

          <Card className="bg-bg-elev border-line shadow-none">
            <CardHeader>
              <CardTitle className="text-ink text-sm uppercase tracking-widest text-ink-soft">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button variant="default" className="bg-accent hover:bg-accent/90 text-white rounded-none">Execute</Button>
                <Button variant="outline" className="border-line text-ink hover:bg-bg-inner rounded-none">Cancel</Button>
              </div>
              <div className="flex gap-2">
                <span className="px-2 py-1 text-[10px] font-mono bg-alert-safe/10 text-alert-safe border border-alert-safe">SAFE</span>
                <span className="px-2 py-1 text-[10px] font-mono bg-alert-warning/10 text-alert-warning border border-alert-warning">ALERT</span>
              </div>
            </CardContent>
          </Card>
        </section>

        <footer className="pt-8 border-t border-line text-center">
          <p className="text-ink-soft text-xs font-mono">© 2026 ANTIGRAVITY FINANCIAL SYSTEMS</p>
        </footer>
      </div>
    </div>
  )
}

export default App
