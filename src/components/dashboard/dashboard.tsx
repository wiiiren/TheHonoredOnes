"use client"

import { RefreshCw, TriangleAlert } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useReplay } from "@/hooks/use-replay"
import { hhmm } from "@/lib/time"

import { Decision } from "./decision"
import { PatientFlow } from "./patient-flow"
import { ReplayControls } from "./replay-controls"
import { AlsoWatching, MovesApplied } from "./side-cards"
import { SiteHeader } from "./site-header"
import { TrustSection } from "./trust-section"

export function Dashboard() {
  const r = useReplay()
  const meta = r.meta

  function apply() {
    const move = r.apply()
    if (move) toast.success(`Applied at ${hhmm(move.at)}`, { description: move.label })
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(1200px_500px_at_15%_-10%,var(--glow),transparent_60%)]">
      <SiteHeader clock={r.clock} playing={r.playing} closed={r.closed} ready={!!meta} />

      <main className="mx-auto flex max-w-7xl flex-col gap-5 px-4 pt-6 pb-12 sm:px-6">
        {r.metaError ? (
          <div className="mx-auto mt-16 flex max-w-md flex-col items-center gap-3 text-center">
            <div className="grid size-12 place-items-center rounded-2xl bg-breach/10 text-breach">
              <TriangleAlert className="size-6" />
            </div>
            <h1 className="text-xl font-bold">The clinic engine is not responding</h1>
            <p className="text-muted-foreground">{r.metaError}</p>
            <Button onClick={r.retry} variant="outline" className="rounded-lg">
              <RefreshCw />
              Try again
            </Button>
          </div>
        ) : !meta ? (
          <>
            <Skeleton className="h-44 rounded-2xl" />
            <Skeleton className="h-56 rounded-2xl" />
            <Skeleton className="h-72 rounded-3xl" />
          </>
        ) : (
          <>
            <h1 className="sr-only">Services Bottleneck Predictor: which outpatient station will pass the {meta.limit}-minute limit next</h1>
            <ReplayControls r={r} />
            <PatientFlow stations={r.screen?.stations ?? null} limit={meta.limit} />

            <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_350px]">
              <Decision
                screen={r.screen}
                error={r.error}
                onApply={apply}
                onRetry={r.retry}
                applying={r.loading}
              />
              <aside className="flex flex-col gap-5">
                {!r.closed && <AlsoWatching items={r.screen?.watching ?? []} onSelect={r.setSelected} />}
                <MovesApplied
                  moves={r.moves}
                  outcome={r.screen?.outcome ?? null}
                  showOutcome={!!r.screen?.show_outcome}
                  limit={meta.limit}
                />
              </aside>
            </div>

            <TrustSection meta={meta} />

            <footer className="pt-1 text-center text-[12.5px] text-muted-foreground">
              {meta.usesMock && (
                <p className="mb-1 text-watch">
                  Demo numbers: the live engine is not connected yet, so this replay is illustrative.
                </p>
              )}
              <p>Prototype on simulated clinic days. Recommends staffing moves only; makes no clinical decisions.</p>
            </footer>
          </>
        )}
      </main>
    </div>
  )
}
