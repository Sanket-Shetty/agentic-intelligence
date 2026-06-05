import React from "react"
import ReactDOM from "react-dom/client"
import { Activity, AlertTriangle, ArrowRight, BarChart3, Database, Gauge, RefreshCw, Search, Sparkles, Timer } from "lucide-react"

import { Card } from "@/components/ui/card"
import { SplineScene } from "@/components/ui/splite"
import { Spotlight } from "@/components/ui/spotlight"
import "./index.css"

type SourceStatus = {
  ok: boolean
  error?: string | null
  found?: boolean | null
}

type IntelligenceReport = {
  input: string
  input_type: string
  order_id?: string | null
  tx_hash?: string | null
  user_address?: string | null
  postgres_data?: Record<string, unknown> | null
  loki_data?: Record<string, unknown> | null
  quotes: Array<Record<string, unknown>>
  mixpanel: {
    events: Array<Record<string, unknown>>
    profile?: Record<string, unknown> | null
    quote_event_count: number
  }
  metrics: {
    settlement_time_seconds?: number | null
    slippage?: {
      quoted_output: number
      actual_output: number
      token_symbol?: string | null
      slippage_bps: number
    } | null
  }
  anomalies: string[]
  source_status: Record<string, SourceStatus>
  summary: string
}

type PendingTransaction = {
  type: string
  request_hash: string
  request_type: string
  request_received_at?: string | null
  origin_chain_id?: number | string | null
  destination_chain_id?: number | string | null
  input_token?: string | null
  output_token?: string | null
  input_amount?: string | null
  created_at?: string | null
  updated_at?: string | null
  extraction_timestamp?: string | null
  router_type?: string | null
  failure_reason?: string | null
  quote_id?: string | null
  integrator_name?: string | null
  input_token_symbol?: string | null
  output_token_symbol?: string | null
  input_amount_usd?: number | string | null
  output_amount_usd?: number | string | null
  pending_mins?: number | string | null
}

type InsightResult = {
  prompt: string
  title: string
  sql: string
  chart_type: "bar" | "line" | "table" | "metric"
  x_key?: string | null
  y_key?: string | null
  explanation: string
  row_count: number
  rows: Array<Record<string, unknown>>
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—"
  return String(value)
}

function App() {
  const [input, setInput] = React.useState("")
  const [inputType, setInputType] = React.useState<"auto" | "tx_hash" | "request_hash">("auto")
  const [includeMixpanel, setIncludeMixpanel] = React.useState(true)
  const [report, setReport] = React.useState<IntelligenceReport | null>(null)
  const [error, setError] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [pendingTransactions, setPendingTransactions] = React.useState<PendingTransaction[]>([])
  const [pendingLoading, setPendingLoading] = React.useState(false)
  const [pendingError, setPendingError] = React.useState("")
  const [insightPrompt, setInsightPrompt] = React.useState("")
  const [insightResult, setInsightResult] = React.useState<InsightResult | null>(null)
  const [insightLoading, setInsightLoading] = React.useState(false)
  const [insightError, setInsightError] = React.useState("")

  const loadPendingTransactions = React.useCallback(async () => {
    setPendingLoading(true)
    setPendingError("")

    try {
      const response = await fetch(`${API_URL}/api/pending-transactions`)
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail ?? "Unable to load pending transactions")
      }
      setPendingTransactions(payload.transactions ?? [])
    } catch (caught) {
      setPendingError(caught instanceof Error ? caught.message : "Unexpected error")
    } finally {
      setPendingLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void loadPendingTransactions()
  }, [loadPendingTransactions])

  async function loadReport(value: string, type: "auto" | "tx_hash" | "request_hash") {
    setLoading(true)
    setError("")
    setReport(null)

    try {
      const response = await fetch(`${API_URL}/api/intelligence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value,
          input_type: type,
          include_mixpanel: includeMixpanel,
          window_hours: 2,
        }),
      })

      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail ?? "Unable to build transaction report")
      }
      setReport(payload)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unexpected error")
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await loadReport(input, inputType)
  }

  async function handlePendingSelect(requestHash: string) {
    setInput(requestHash)
    setInputType("request_hash")
    await loadReport(requestHash, "request_hash")
  }

  async function handleInsightSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setInsightLoading(true)
    setInsightError("")
    setInsightResult(null)

    try {
      const response = await fetch(`${API_URL}/api/query-insights`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: insightPrompt }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail ?? "Unable to generate insight")
      }
      setInsightResult(payload)
    } catch (caught) {
      setInsightError(caught instanceof Error ? caught.message : "Unexpected error")
    } finally {
      setInsightLoading(false)
    }
  }

  return (
    <main className="min-h-screen">
      <section className="relative overflow-hidden border-b border-white/10">
        <Spotlight className="-top-52 left-10 md:left-96 md:-top-32" fill="#ffffff" />
        <div className="mx-auto grid min-h-[520px] max-w-7xl grid-cols-1 gap-8 px-5 py-8 md:grid-cols-[1.05fr_.95fr] md:px-8">
          <div className="relative z-10 flex flex-col justify-center">
            <div className="mb-5 flex w-fit items-center gap-2 rounded-full border border-teal-300/30 bg-teal-300/10 px-3 py-1 text-sm text-teal-100">
              <Sparkles className="h-4 w-4" />
              Socket transaction intelligence
            </div>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-white md:text-6xl">
              Trace a bridge transaction across product, backend, and execution data.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
              Submit a transaction hash or request hash to stitch Metabase records,
              Loki settlement details, and Mixpanel journey events into one operator view.
            </p>

            <form onSubmit={handleSubmit} className="mt-8 max-w-2xl">
              <div className="flex flex-col gap-3 rounded-lg border border-white/12 bg-black/30 p-3 backdrop-blur md:flex-row">
                <div className="flex min-w-0 flex-1 items-center gap-3 rounded-md border border-white/10 bg-white/[0.06] px-3">
                  <Search className="h-5 w-5 shrink-0 text-slate-400" />
                  <input
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="0x transaction hash or request hash"
                    className="h-12 min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-teal-300 px-5 text-sm font-semibold text-slate-950 transition hover:bg-teal-200 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Querying" : "Run report"}
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-300">
                <select
                  value={inputType}
                  onChange={(event) => setInputType(event.target.value as typeof inputType)}
                  className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-white outline-none"
                >
                  <option value="auto">Auto detect</option>
                  <option value="tx_hash">Transaction hash</option>
                  <option value="request_hash">Request hash</option>
                </select>
                <label className="inline-flex h-10 items-center gap-2 rounded-md border border-white/10 bg-slate-950 px-3">
                  <input
                    type="checkbox"
                    checked={includeMixpanel}
                    onChange={(event) => setIncludeMixpanel(event.target.checked)}
                    className="h-4 w-4 accent-teal-300"
                  />
                  Mixpanel
                </label>
              </div>
            </form>
          </div>

          <div className="relative min-h-[360px] overflow-hidden">
            <SplineScene
              scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
              className="h-full min-h-[360px] w-full"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-8 md:px-8">
        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-400/30 bg-red-500/10 p-4 text-red-100">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {!report && !error && (
          <div className="grid gap-4 md:grid-cols-3">
            <InfoPanel icon={<Database />} title="Metabase" body="Backend order, fee, quote, status, and user records." />
            <InfoPanel icon={<Activity />} title="Loki" body="On-chain execution, hashes, settlement timing, and bridge status." />
            <InfoPanel icon={<Gauge />} title="Mixpanel" body="Quote journey events and user profile context around the transaction." />
          </div>
        )}

        {report && <ReportView report={report} />}

        <PendingTransactionsTable
          error={pendingError}
          loading={pendingLoading}
          onRefresh={loadPendingTransactions}
          onSelect={handlePendingSelect}
          rows={pendingTransactions}
        />

        <InsightQueryPanel
          error={insightError}
          loading={insightLoading}
          onPromptChange={setInsightPrompt}
          onSubmit={handleInsightSubmit}
          prompt={insightPrompt}
          result={insightResult}
        />
      </section>
    </main>
  )
}

function InfoPanel({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <Card className="border-white/10 bg-white/[0.04] p-5">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-teal-300/12 text-teal-200">
        {icon}
      </div>
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
    </Card>
  )
}

function ReportView({ report }: { report: IntelligenceReport }) {
  const slippage = report.metrics.slippage
  const sourceEntries = Object.entries(report.source_status)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Unified report</h2>
        <p className="mt-2 text-slate-300">{report.summary}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Metric icon={<Database />} label="Order" value={formatValue(report.order_id)} />
        <Metric icon={<Activity />} label="User" value={formatValue(report.user_address)} />
        <Metric icon={<Timer />} label="Settlement" value={report.metrics.settlement_time_seconds ? `${report.metrics.settlement_time_seconds}s` : "—"} />
        <Metric icon={<Gauge />} label="Slippage" value={slippage ? `${slippage.slippage_bps} bps` : "—"} />
      </div>

      {report.anomalies.length > 0 && (
        <div className="rounded-lg border border-amber-300/30 bg-amber-300/10 p-4">
          <h3 className="flex items-center gap-2 font-semibold text-amber-100">
            <AlertTriangle className="h-5 w-5" />
            Anomalies
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-amber-50">
            {report.anomalies.map((anomaly) => (
              <li key={anomaly}>{anomaly}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <DataBlock title="Metabase transaction" data={report.postgres_data} />
        <DataBlock title="Loki execution" data={report.loki_data} />
        <DataBlock title={`Quotes (${report.quotes.length})`} data={report.quotes.slice(0, 5)} />
        <DataBlock title={`Mixpanel events (${report.mixpanel.events.length})`} data={report.mixpanel.events.slice(0, 5)} />
      </div>

      {sourceEntries.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <h3 className="font-semibold text-white">Source status</h3>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {sourceEntries.map(([name, status]) => (
              <div key={name} className="flex items-start justify-between gap-4 rounded-md bg-black/25 px-3 py-2 text-sm">
                <span className="text-slate-300">{name}</span>
                <span className={status.ok ? "text-teal-200" : "text-red-200"}>
                  {status.ok ? (status.found === false ? "no rows" : "connected") : status.error}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Card className="border-white/10 bg-white/[0.04] p-4">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <span className="text-teal-200">{icon}</span>
        {label}
      </div>
      <div className="mt-3 break-all text-lg font-semibold text-white">{value}</div>
    </Card>
  )
}

function DataBlock({ title, data }: { title: string; data: unknown }) {
  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/70 p-4">
      <h3 className="font-semibold text-white">{title}</h3>
      <pre className="mt-3 max-h-80 overflow-auto rounded-md bg-black/40 p-3 text-xs leading-5 text-slate-300">
        {JSON.stringify(data ?? {}, null, 2)}
      </pre>
    </div>
  )
}

function compactHash(value: string) {
  if (value.length <= 18) return value
  return `${value.slice(0, 10)}...${value.slice(-8)}`
}

function formatNumber(value: unknown, digits = 2) {
  const number = Number(value)
  if (!Number.isFinite(number)) return "—"
  return number.toLocaleString(undefined, { maximumFractionDigits: digits })
}

function formatDateTime(value: unknown) {
  if (!value) return "—"
  const date = new Date(String(value))
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function PendingTransactionsTable({
  error,
  loading,
  onRefresh,
  onSelect,
  rows,
}: {
  error: string
  loading: boolean
  onRefresh: () => void
  onSelect: (requestHash: string) => void
  rows: PendingTransaction[]
}) {
  return (
    <section className="mt-8 rounded-lg border border-white/10 bg-white/[0.04]">
      <div className="flex flex-col gap-4 border-b border-white/10 p-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Pending transactions</h2>
          <p className="mt-1 text-sm text-slate-400">
            {loading ? "Loading stuck transactions" : `${rows.length} stuck transactions from the last 10 days`}
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-white/10 bg-slate-950 px-3 text-sm font-medium text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="m-4 flex items-start gap-3 rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
          <thead className="bg-black/25 text-xs uppercase text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Request hash</th>
              <th className="px-4 py-3 font-medium">Pending</th>
              <th className="px-4 py-3 font-medium">Route</th>
              <th className="px-4 py-3 font-medium">Tokens</th>
              <th className="px-4 py-3 font-medium">USD</th>
              <th className="px-4 py-3 font-medium">Integrator</th>
              <th className="px-4 py-3 font-medium">Request type</th>
              <th className="px-4 py-3 font-medium">Received</th>
              <th className="px-4 py-3 font-medium">Router</th>
              <th className="px-4 py-3 font-medium">Failure</th>
              <th className="px-4 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {rows.length === 0 && !loading && (
              <tr>
                <td className="px-4 py-8 text-center text-slate-400" colSpan={12}>
                  No stuck pending transactions found.
                </td>
              </tr>
            )}
            {loading && rows.length === 0 && (
              <tr>
                <td className="px-4 py-8 text-center text-slate-400" colSpan={12}>
                  Loading pending transactions...
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={`${row.type}-${row.request_hash}`} className="align-top text-slate-300 hover:bg-white/[0.03]">
                <td className="max-w-[220px] px-4 py-3 text-white">{row.type}</td>
                <td className="px-4 py-3 font-mono text-xs text-teal-200" title={row.request_hash}>
                  {compactHash(row.request_hash)}
                </td>
                <td className="px-4 py-3">{formatNumber(row.pending_mins, 1)}m</td>
                <td className="px-4 py-3">
                  {formatValue(row.origin_chain_id)} → {formatValue(row.destination_chain_id)}
                </td>
                <td className="px-4 py-3">
                  {formatValue(row.input_token_symbol)} → {formatValue(row.output_token_symbol)}
                </td>
                <td className="px-4 py-3">${formatNumber(row.output_amount_usd ?? row.input_amount_usd, 2)}</td>
                <td className="px-4 py-3">{formatValue(row.integrator_name)}</td>
                <td className="px-4 py-3">{formatValue(row.request_type)}</td>
                <td className="px-4 py-3">{formatDateTime(row.request_received_at)}</td>
                <td className="px-4 py-3">{formatValue(row.router_type)}</td>
                <td className="max-w-[220px] px-4 py-3">{formatValue(row.failure_reason)}</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onSelect(row.request_hash)}
                    className="inline-flex h-8 items-center justify-center rounded-md bg-teal-300 px-3 text-xs font-semibold text-slate-950 transition hover:bg-teal-200"
                  >
                    Load
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function InsightQueryPanel({
  error,
  loading,
  onPromptChange,
  onSubmit,
  prompt,
  result,
}: {
  error: string
  loading: boolean
  onPromptChange: (value: string) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  prompt: string
  result: InsightResult | null
}) {
  return (
    <section className="mt-8 rounded-lg border border-white/10 bg-white/[0.04]">
      <div className="border-b border-white/10 p-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-teal-200" />
          <h2 className="text-xl font-semibold text-white">Ask transaction data</h2>
        </div>
        <p className="mt-1 text-sm text-slate-400">
          Ask in plain English. The agent writes read-only SQL using successful transaction logic, quoteId joins, and chain names.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-3 p-4">
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          placeholder="Example: total volume done on Base chain as source chain in last 7 days"
          className="min-h-24 w-full resize-y rounded-md border border-white/10 bg-slate-950 p-3 text-sm leading-6 text-white outline-none placeholder:text-slate-500 focus:border-teal-300/70"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal-300 px-4 text-sm font-semibold text-slate-950 transition hover:bg-teal-200 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Generating" : "Generate insight"}
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      {error && (
        <div className="mx-4 mb-4 flex items-start gap-3 rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && <InsightResultView result={result} />}
    </section>
  )
}

function InsightResultView({ result }: { result: InsightResult }) {
  return (
    <div className="space-y-4 border-t border-white/10 p-4">
      <div>
        <h3 className="text-lg font-semibold text-white">{result.title}</h3>
        <p className="mt-1 text-sm text-slate-400">
          {result.explanation || `${result.row_count} rows returned`}
        </p>
      </div>

      <InsightVisualization result={result} />

      <details className="rounded-md border border-white/10 bg-slate-950/70">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-200">Generated SQL</summary>
        <pre className="max-h-80 overflow-auto border-t border-white/10 p-4 text-xs leading-5 text-slate-300">
          {result.sql}
        </pre>
      </details>

      <InsightTable rows={result.rows} />
    </div>
  )
}

function InsightVisualization({ result }: { result: InsightResult }) {
  if (result.row_count === 0) {
    return (
      <div className="rounded-md border border-white/10 bg-black/20 p-6 text-center text-sm text-slate-400">
        No rows returned.
      </div>
    )
  }

  if (result.chart_type === "metric") {
    const firstRow = result.rows[0] ?? {}
    const key = result.y_key ?? Object.keys(firstRow).find((column) => Number.isFinite(Number(firstRow[column])))
    return (
      <div className="rounded-md border border-white/10 bg-black/20 p-6">
        <div className="text-sm text-slate-400">{key ?? "Value"}</div>
        <div className="mt-2 text-4xl font-semibold text-white">{formatNumber(key ? firstRow[key] : undefined, 2)}</div>
      </div>
    )
  }

  if ((result.chart_type === "bar" || result.chart_type === "line") && result.x_key && result.y_key) {
    const values = result.rows
      .map((row) => ({
        label: formatValue(row[result.x_key as string]),
        value: Number(row[result.y_key as string]),
      }))
      .filter((row) => Number.isFinite(row.value))
      .slice(0, 12)
    const maxValue = Math.max(...values.map((row) => row.value), 0)

    return (
      <div className="space-y-3 rounded-md border border-white/10 bg-black/20 p-4">
        {values.length === 0 && <div className="text-sm text-slate-400">No numeric chart values found.</div>}
        {values.map((row) => {
          const width = maxValue > 0 ? Math.max((row.value / maxValue) * 100, 2) : 0
          return (
            <div key={`${row.label}-${row.value}`} className="grid grid-cols-[180px_1fr_120px] items-center gap-3 text-sm">
              <div className="truncate text-slate-300" title={row.label}>{row.label}</div>
              <div className="h-3 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-teal-300" style={{ width: `${width}%` }} />
              </div>
              <div className="text-right font-medium text-white">{formatNumber(row.value, 2)}</div>
            </div>
          )
        })}
      </div>
    )
  }

  return null
}

function InsightTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 16)

  if (rows.length === 0 || columns.length === 0) {
    return null
  }

  return (
    <div className="overflow-x-auto rounded-md border border-white/10">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-black/25 text-xs uppercase text-slate-400">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-3 py-2 font-medium">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {rows.slice(0, 100).map((row, index) => (
            <tr key={index} className="text-slate-300">
              {columns.map((column) => (
                <td key={column} className="max-w-[260px] truncate px-3 py-2" title={formatValue(row[column])}>
                  {formatValue(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
