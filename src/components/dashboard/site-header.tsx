"use client"

import { Activity, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { cn } from "cn"

import { Button } from "@/components/ui/button"
import { hhmm } from "@/lib/time"

export function SiteHeader({ clock, playing, closed, ready }: {
  clock: number
  playing: boolean
  closed: boolean
  ready: boolean
}) {
  const { resolvedTheme, setTheme } = useTheme()
  const mode = closed ? "Clinic closed" : playing ? "Replaying" : "Paused"

  return (
    <header className="sticky top-0 z-30 border-b bg-background/70 backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 text-white shadow-[0_6px_16px_-6px_var(--brand)]">
            <Activity className="size-[18px]" strokeWidth={2.4} />
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">Services Bottleneck Predictor</div>
            <div className="hidden text-xs text-muted-foreground sm:block">Hospital Outpatient Services</div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end leading-none">
            <span className="hidden text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase sm:block">
              Clinic time
            </span>
            <span className="tabular text-2xl font-bold tracking-tight" aria-label="Clinic time">
              {ready ? hhmm(clock) : "--:--"}
            </span>
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-xs font-semibold whitespace-nowrap shadow-xs",
              playing && !closed ? "text-ok" : "text-muted-foreground",
            )}
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                closed ? "bg-indigo-500" : playing ? "animate-ping-soft bg-ok" : "bg-muted-foreground",
              )}
            />
            {mode}
          </span>
          <Button
            variant="outline"
            size="icon"
            className="size-9 rounded-xl"
            aria-label="Switch between light and dark theme"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          >
            <Sun className="hidden size-4 dark:block" />
            <Moon className="size-4 dark:hidden" />
          </Button>
        </div>
      </div>
    </header>
  )
}
