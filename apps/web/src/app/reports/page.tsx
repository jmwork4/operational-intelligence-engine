"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { FileText, Calendar, Download, TrendingUp, PieChart as PieIcon, Target, FileSpreadsheet } from "lucide-react";

// -- Mock data ---------------------------------------------------------------

const eventsByDay = [
  { day: "Mon", events: 1820 },
  { day: "Tue", events: 2140 },
  { day: "Wed", events: 1960 },
  { day: "Thu", events: 2580 },
  { day: "Fri", events: 2310 },
  { day: "Sat", events: 980 },
  { day: "Sun", events: 740 },
];

const alertsBySeverity = [
  { name: "Critical", value: 12, color: "#ef4444" },
  { name: "High", value: 28, color: "#f97316" },
  { name: "Medium", value: 45, color: "#eab308" },
  { name: "Low", value: 18, color: "#22c55e" },
];

const slaCompliance = [
  { week: "W1", rate: 94.2 },
  { week: "W2", rate: 96.1 },
  { week: "W3", rate: 91.8 },
  { week: "W4", rate: 97.5 },
  { week: "W5", rate: 95.3 },
  { week: "W6", rate: 98.1 },
];

const reportTypes = [
  {
    id: "daily",
    title: "Daily Summary",
    description: "Events, alerts, and entity activity for a single day",
    icon: FileText,
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    id: "weekly",
    title: "Weekly Summary",
    description: "Trends, rule triggers, and SLA compliance for a week",
    icon: TrendingUp,
    color: "text-teal-600",
    bg: "bg-teal-50",
  },
  {
    id: "sla",
    title: "SLA Compliance",
    description: "On-time rates, delays, and breach analysis",
    icon: Target,
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
  {
    id: "export",
    title: "Custom Export",
    description: "Export events or alerts as CSV with custom filters",
    icon: FileSpreadsheet,
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
];

// -- Component ---------------------------------------------------------------

export default function ReportsPage() {
  const [startDate, setStartDate] = useState("2026-03-10");
  const [endDate, setEndDate] = useState("2026-03-16");
  const [activeReport, setActiveReport] = useState<string | null>("daily");

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Reports</h2>
        <p className="text-sm text-gray-500 mt-1">
          Generate summaries, analyze SLA compliance, and export data
        </p>
      </div>

      {/* Report type cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {reportTypes.map((rt) => {
          const Icon = rt.icon;
          const isActive = activeReport === rt.id;
          return (
            <button
              key={rt.id}
              onClick={() => setActiveReport(rt.id)}
              className={`text-left bg-white rounded-xl border p-4 transition-all ${
                isActive
                  ? "border-teal-300 ring-2 ring-teal-100"
                  : "border-gray-200 hover:border-gray-300 hover:shadow-sm"
              }`}
            >
              <div className={`w-9 h-9 rounded-lg ${rt.bg} flex items-center justify-center mb-3`}>
                <Icon className={`w-4.5 h-4.5 ${rt.color}`} />
              </div>
              <h3 className="text-sm font-semibold text-gray-900">{rt.title}</h3>
              <p className="text-xs text-gray-500 mt-1">{rt.description}</p>
            </button>
          );
        })}
      </div>

      {/* Date range + generate */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
            <div className="relative">
              <Calendar className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
            <div className="relative">
              <Calendar className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>
          </div>
          <button className="px-5 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors">
            Generate Report
          </button>
          <div className="flex items-center gap-2 ml-auto">
            <button className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
              <Download className="w-4 h-4" />
              CSV
            </button>
            <button className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
              <Download className="w-4 h-4" />
              PDF
            </button>
          </div>
        </div>
      </div>

      {/* Report preview with charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Events by Day - Bar chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Events by Day</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={eventsByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: "#6b7280" }} />
                <YAxis tick={{ fontSize: 12, fill: "#6b7280" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    fontSize: "13px",
                  }}
                />
                <Bar dataKey="events" fill="#0d9488" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Alerts by Severity - Pie chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Alerts by Severity</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={alertsBySeverity}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  dataKey="value"
                  stroke="none"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {alertsBySeverity.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    fontSize: "13px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* SLA Compliance Trend - Line chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">SLA Compliance Trend</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={slaCompliance}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#6b7280" }} />
              <YAxis
                domain={[85, 100]}
                tick={{ fontSize: 12, fill: "#6b7280" }}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
                formatter={(value: number) => [`${value}%`, "SLA Rate"]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="rate"
                name="SLA Compliance %"
                stroke="#7c3aed"
                strokeWidth={2}
                dot={{ fill: "#7c3aed", r: 4 }}
                activeDot={{ r: 6 }}
              />
              {/* Target line at 95% */}
              <Line
                type="monotone"
                dataKey={() => 95}
                name="Target (95%)"
                stroke="#d1d5db"
                strokeDasharray="5 5"
                strokeWidth={1}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Events", value: "12,530" },
          { label: "Alerts Generated", value: "103" },
          { label: "Alerts Resolved", value: "91" },
          { label: "Avg Resolution", value: "34 min" },
        ].map((m) => (
          <div key={m.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-2xl font-bold text-gray-900">{m.value}</p>
            <p className="text-sm text-gray-500 mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
