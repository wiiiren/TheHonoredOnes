"use client"

import {
  ArrowDown,
  ArrowUp,
  ChartBarBig,
  Check,
  ChevronDown,
  CircleCheck,
  Clock,
  Eye,
  Gauge,
  GitBranch,
  MapPin,
  Megaphone,
  Moon,
  RefreshCw,
  Sparkles,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { cn } from "cn"

import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Skeleton } from "@/components/ui/skeleton"
import type { ActionCard as Card, Mode, Screen } from "@/lib/types"

function Disclosure({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children: React.ReactNode }) {
  return (
    <Collapsible className="rounded-xl border bg-card">
      <CollapsibleTrigger className="group flex w-full items-center gap-2 rounded-xl px-3.5 py-2.5 text-left text-sm font-semibold text-foreground/80 outline-none hover:bg-muted/60 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50">
        <Icon className="size-4" />
        {title}
        <ChevronDown className="ml-auto size-4 text-muted-foreground transition-transform group-data-[panel-open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-3.5 pb-3.5">{children}</CollapsibleContent>
    </Collapsible>
  )
}

function Causes({ card }: { card: Card }) {
  return (
    <>
      <div className="mt-1 flex flex-col gap-2.5">
        {card.causes.map((c) => (
          <div key={c.label} className="grid grid-cols-[110px_1fr_52px] items-center gap-3 sm:grid-cols-[130px_1fr_56px]">
            <span className="text-[13.5px] font-medium text-foreground/80">{c.label}</span>
            <div className="h-2.5 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn(
                  "h-full rounded-full",
                  c.top ? "bg-gradient-to-r from-brand to-brand-strong" : "bg-muted-foreground/40",
                )}
                initial={{ width: 0 }}
                animate={{ width: `${c.width}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <span className="tabular text-right text-[13px] font-semibold">{c.minutes} min</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[13px] text-muted-foreground">{card.causes_note}</p>
    </>
  )
}

function WhatIfs({ card }: { card: Card }) {
  return (
    <ul className="flex flex-col gap-2">
      {card.what_ifs.map((w) => (
        <li key={w.label} className="rounded-lg bg-muted/60 px-3 py-2.5">
          <div className="text-sm font-semibold">{w.label}</div>
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs font-medium">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-2 py-0.5",
                w.saved > 0 ? "bg-ok/10 text-ok" : "border bg-card text-muted-foreground",
              )}
            >
              {w.saved < 0 ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />}
              {w.effect}
            </span>
            <span className="inline-flex items-center gap-1 rounded-md border bg-card px-2 py-0.5 text-muted-foreground">
              <ArrowUp className="size-3" />
              Adds {w.added} min elsewhere
            </span>
            <span className="rounded-md border bg-card px-2 py-0.5 text-muted-foreground">Busiest after: {w.after}</span>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ActionCard({ card, onApply, applying }: { card: Card; onApply: () => void; applying: boolean }) {
  const urgent = card.tone === "urgent"
  return (
    <section
      aria-live="polite"
      className={cn(
        "relative overflow-hidden rounded-3xl border bg-card p-5 shadow-[0_24px_48px_-20px_rgb(15_23_42/0.25)] sm:p-7",
        "before:absolute before:inset-x-0 before:top-0 before:h-1",
        urgent ? "before:bg-gradient-to-r before:from-breach before:to-orange-500" : "before:bg-gradient-to-r before:from-watch before:to-yellow-400",
      )}
    >
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute -top-24 -left-24 size-72 rounded-full blur-3xl",
          urgent ? "bg-breach/10" : "bg-watch/10",
        )}
      />
      <div className="relative">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span
            className={cn(
              "inline-flex items-center gap-2.5 text-xs font-bold tracking-[0.1em] uppercase",
              urgent ? "text-breach" : "text-watch",
            )}
          >
            <span className="animate-ping-soft size-2 rounded-full bg-current" />
            {card.label}
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[13px] font-semibold text-white dark:text-black",
              urgent ? "bg-breach" : "bg-watch",
            )}
          >
            <Clock className="size-3.5" />
            {card.deadline}
          </span>
        </div>

        <div className="mt-4 flex flex-wrap gap-1.5">
          <span className="inline-flex items-center gap-1.5 rounded-md border bg-muted/60 px-2 py-0.5 text-[12.5px] font-semibold text-foreground/80">
            <MapPin className="size-3.5" />
            {card.station_name}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border bg-muted/60 px-2 py-0.5 text-[12.5px] font-semibold text-foreground/80">
            <Gauge className="size-3.5" />
            {card.chance}% chance
          </span>
        </div>

        <h2 className="mt-3 text-[26px] leading-[1.15] font-bold tracking-tight text-balance sm:text-[32px]">
          {card.title}
        </h2>
        <p className="mt-3 max-w-[68ch] text-base leading-relaxed text-foreground/75">
          {card.what} <strong className="font-semibold text-foreground">{card.why_head}</strong> {card.why_rest}{" "}
          {card.affected}
        </p>
        {card.rank && <p className="mt-2 text-[13.5px] font-medium text-muted-foreground">{card.rank}</p>}

        {card.helps ? (
          <div className="mt-5 grid gap-4 md:grid-cols-[auto_1fr]">
            <Button
              onClick={onApply}
              disabled={applying}
              className="h-auto min-h-13 rounded-2xl bg-gradient-to-b from-teal-500 to-teal-700 px-6 text-[15px] font-semibold text-white shadow-[0_10px_24px_-10px_var(--brand-strong)] transition-[filter,transform] hover:brightness-110 active:scale-[0.97]"
            >
              <Check className="size-[18px]" strokeWidth={2.6} />
              Apply move
            </Button>
            <div className="rounded-xl border bg-muted/50 px-3.5 py-3">
              <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-[0.08em] text-brand uppercase">
                <Sparkles className="size-3.5" />
                Expected effect
              </div>
              <p className="mt-1 text-sm leading-relaxed text-foreground/75">{card.effect}</p>
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-xl bg-watch/10 px-3.5 py-3">
            <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-[0.08em] text-watch uppercase">
              <Megaphone className="size-3.5" />
              {card.no_move_title}
            </div>
            <p className="mt-1 text-sm leading-relaxed text-foreground/75">{card.no_move}</p>
          </div>
        )}

        <div className="mt-5 flex flex-col gap-2">
          <Disclosure icon={ChartBarBig} title="Why?">
            <Causes card={card} />
          </Disclosure>
          {card.what_ifs.length > 0 && (
            <Disclosure icon={GitBranch} title="What if?">
              <WhatIfs card={card} />
            </Disclosure>
          )}
        </div>
      </div>
    </section>
  )
}

const NOTE: Record<Exclude<Mode, "alert">, { icon: LucideIcon; tint: string }> = {
  calm: { icon: CircleCheck, tint: "bg-ok/10 text-ok" },
  watch: { icon: Eye, tint: "bg-watch/12 text-watch" },
  closed: { icon: Moon, tint: "bg-indigo-500/12 text-indigo-500" },
  error: { icon: TriangleAlert, tint: "bg-breach/10 text-breach" },
}

function StateNote({ mode, title, body, onRetry }: { mode: Exclude<Mode, "alert">; title: string; body: string; onRetry?: () => void }) {
  const { icon: Icon, tint } = NOTE[mode]
  return (
    <section aria-live="polite" className="flex items-start gap-4 rounded-3xl border bg-card p-6 shadow-sm sm:p-7">
      <div className={cn("grid size-12 shrink-0 place-items-center rounded-2xl", tint)}>
        <Icon className="size-[22px]" />
      </div>
      <div>
        <h2 className="text-[22px] font-bold tracking-tight">{title}</h2>
        <p className="mt-1.5 text-[15.5px] leading-relaxed text-foreground/75">{body}</p>
        {onRetry && (
          <Button variant="outline" onClick={onRetry} className="mt-4 rounded-lg">
            <RefreshCw />
            Try again
          </Button>
        )}
      </div>
    </section>
  )
}

export function Decision({ screen, error, onApply, onRetry, applying }: {
  screen: Screen | null
  error: string | null
  onApply: () => void
  onRetry: () => void
  applying: boolean
}) {
  if (error) return <StateNote mode="error" title="Something went wrong" body={error} onRetry={onRetry} />
  if (!screen) return <Skeleton className="h-72 rounded-3xl" />

  const key = screen.mode === "alert" ? `alert-${screen.card.station}-${screen.card.action_id}` : screen.mode
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={key}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
      >
        {screen.mode === "alert" ? (
          <ActionCard card={screen.card} onApply={onApply} applying={applying} />
        ) : (
          <StateNote mode={screen.mode} title={screen.note_title} body={screen.note_body} />
        )}
      </motion.div>
    </AnimatePresence>
  )
}
