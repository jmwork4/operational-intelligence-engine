"use client";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const latencyData = [
  { time: "00:00", avg_ms: 2800, p95_ms: 4200 },
  { time: "02:00", avg_ms: 2600, p95_ms: 3900 },
  { time: "04:00", avg_ms: 2400, p95_ms: 3600 },
  { time: "06:00", avg_ms: 2900, p95_ms: 4400 },
  { time: "08:00", avg_ms: 3400, p95_ms: 5100 },
  { time: "10:00", avg_ms: 3200, p95_ms: 4800 },
  { time: "12:00", avg_ms: 3100, p95_ms: 4600 },
  { time: "14:00", avg_ms: 3500, p95_ms: 5200 },
  { time: "16:00", avg_ms: 3300, p95_ms: 4900 },
  { time: "18:00", avg_ms: 2900, p95_ms: 4300 },
  { time: "20:00", avg_ms: 2700, p95_ms: 4000 },
  { time: "22:00", avg_ms: 2500, p95_ms: 3700 },
];

const tokenData = [
  { time: "00:00", input: 32400, output: 8900 },
  { time: "02:00", input: 18200, output: 5100 },
  { time: "04:00", input: 12100, output: 3400 },
  { time: "06:00", input: 28500, output: 7800 },
  { time: "08:00", input: 78900, output: 21600 },
  { time: "10:00", input: 92400, output: 25300 },
  { time: "12:00", input: 85600, output: 23400 },
  { time: "14:00", input: 98200, output: 26900 },
  { time: "16:00", input: 88100, output: 24100 },
  { time: "18:00", input: 64300, output: 17600 },
  { time: "20:00", input: 42800, output: 11700 },
  { time: "22:00", input: 35200, output: 9600 },
];

const toolUsageData = [
  { tool: "query_events", calls: 156, color: "#0d9488" },
  { tool: "get_event_stats", calls: 89, color: "#14b8a6" },
  { tool: "search_documents", calls: 78, color: "#2dd4bf" },
  { tool: "get_alert_summary", calls: 62, color: "#5eead4" },
  { tool: "get_system_health", calls: 27, color: "#99f6e4" },
];

const policyGuardLog = [
  { time: "14:23", type: "input", result: "pass", risk: 0.02, detail: "Clean query" },
  { time: "14:18", type: "output", result: "pass", risk: 0.04, detail: "Response validated" },
  { time: "14:12", type: "input", result: "blocked", risk: 0.92, detail: "Prompt injection detected" },
  { time: "14:05", type: "output", result: "pass", risk: 0.08, detail: "Low risk, no PII" },
  { time: "13:58", type: "input", result: "pass", risk: 0.01, detail: "Clean query" },
  { time: "13:51", type: "input", result: "blocked", risk: 0.85, detail: "System prompt extraction attempt" },
];

const promptVersions = [
  { name: "general_query", version: 3, status: "active", eval_score: 94.2, last_updated: "Mar 15, 2026" },
  { name: "summarization", version: 2, status: "active", eval_score: 91.8, last_updated: "Mar 14, 2026" },
  { name: "classification", version: 1, status: "active", eval_score: 88.5, last_updated: "Mar 12, 2026" },
  { name: "extraction", version: 2, status: "evaluating", eval_score: 82.1, last_updated: "Mar 16, 2026" },
];

export default function AIObservabilityPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">AI Observability</h2>
        <p className="text-sm text-gray-500 mt-1">
          Model performance, token usage, and pipeline health — last 24 hours
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: "Total Queries", value: "284", detail: "Today" },
          { label: "Avg Latency", value: "3.2s", detail: "Target < 5s" },
          { label: "Tokens Used", value: "1.14M", detail: "892K in / 246K out" },
          { label: "Tool Calls", value: "412", detail: "3 failures (0.7%)" },
          { label: "Context Util", value: "62.4%", detail: "Of 128K budget" },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">{kpi.label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{kpi.value}</p>
            <p className="text-xs text-gray-400 mt-1">{kpi.detail}</p>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Latency Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Response Latency</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={latencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickFormatter={(v) => `${(v / 1000).toFixed(1)}s`} />
              <Tooltip
                formatter={(value: number) => [`${(value / 1000).toFixed(2)}s`]}
                contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
              />
              <Area type="monotone" dataKey="p95_ms" stroke="#fdba74" fill="#fed7aa" fillOpacity={0.4} name="P95" />
              <Area type="monotone" dataKey="avg_ms" stroke="#0d9488" fill="#ccfbf1" fillOpacity={0.6} name="Average" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Token Usage Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Token Usage</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={tokenData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} />
              <Tooltip
                formatter={(value: number) => [`${(value / 1000).toFixed(1)}K tokens`]}
                contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
              />
              <Area type="monotone" dataKey="input" stroke="#6366f1" fill="#e0e7ff" fillOpacity={0.5} name="Input" />
              <Area type="monotone" dataKey="output" stroke="#0d9488" fill="#ccfbf1" fillOpacity={0.5} name="Output" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Tool Usage */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Tool Usage</h3>
          <div className="space-y-3">
            {toolUsageData.map((tool) => (
              <div key={tool.tool}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600 font-mono">{tool.tool}</span>
                  <span className="text-xs font-medium text-gray-900">{tool.calls}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${(tool.calls / 156) * 100}%`,
                      backgroundColor: tool.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Policy Guard Log */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Policy Guard Activity</h3>
          <div className="space-y-2.5">
            {policyGuardLog.map((entry, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-12 flex-shrink-0">{entry.time}</span>
                <span className={`px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                  entry.type === "input" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"
                }`}>
                  {entry.type}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                  entry.result === "pass" ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"
                }`}>
                  {entry.result}
                </span>
                <span className="text-xs text-gray-500 truncate">{entry.detail}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Prompt Registry */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Prompt Registry</h3>
          <div className="space-y-3">
            {promptVersions.map((prompt) => (
              <div key={prompt.name} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-900">{prompt.name}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    prompt.status === "active" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                  }`}>
                    {prompt.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span>v{prompt.version}</span>
                  <span>&middot;</span>
                  <span>Eval: {prompt.eval_score}%</span>
                  <span>&middot;</span>
                  <span>{prompt.last_updated}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
