// Shapes returned by api/index.py (built in presenter/view.py).

export type Status = "ok" | "watch" | "breach" | "over"
export type Mode = "calm" | "watch" | "alert" | "closed" | "error"

export interface DayOption {
  name: string
  tag: string
  icon: string
}

export interface Metric {
  value: string
  caption: string
}

export interface Meta {
  open: number
  close: number
  tick: number
  limit: number
  defaultDay: string
  days: DayOption[]
  metrics: Metric[]
  notes: string[]
  assumptions: string[]
  testDays: number | null
  usesMock: boolean
}

export interface StationView {
  key: string
  name: string
  wait_now: number
  trend: string
  trend_dir: "up" | "down" | "flat"
  status: Status
  status_word: string
  chance: number
  staff: string
  waiting: number
  fill: number
  focus: boolean
}

export interface CauseBar {
  label: string
  minutes: number
  width: number
  top: boolean
}

export interface WhatIf {
  label: string
  saved: number
  added: number
  after: string
}

export interface ActionCard {
  station: string
  station_name: string
  label: string
  title: string
  tone: "urgent" | "warn"
  deadline: string
  chance: number
  what: string
  why_head: string
  why_rest: string
  affected: string
  rank: string
  helps: boolean
  action_id: string
  action_label: string
  effect: string
  no_move_title: string
  no_move: string
  causes: CauseBar[]
  causes_note: string
  what_ifs: WhatIf[]
}

export interface Watching {
  station: string
  name: string
  when: string
  cause: string
  tone: "watch" | "breach"
}

export interface Outcome {
  without_pct: number
  with_pct: number
  without_label: string
  with_label: string
}

export interface Screen {
  mode: Mode
  stations: StationView[]
  card: ActionCard
  note_title: string
  note_body: string
  watching: Watching[]
  outcome: Outcome
  show_outcome: boolean
}

export interface AppliedMove {
  id: string
  label: string
  at: number
}
