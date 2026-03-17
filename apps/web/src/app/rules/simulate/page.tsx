"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Play, Zap } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const chartData = [
  { day: "Mar 1", triggers: 2 },
  { day: "Mar 3", triggers: 0 },
  { day: "Mar 5", triggers: 3 },
  { day: "Mar 7", triggers: 1 },
  { day: "Mar 8", triggers: 4 },
  { day: "Mar 9", triggers: 0 },
  { day: "Mar 10", triggers: 2 },
  { day: "Mar 11", triggers: 1 },
  { day: "Mar 12", triggers: 3 },
  { day: "Mar 13", triggers: 0 },
  { day: "Mar 14", triggers: 5 },
  { day: "Mar 15", triggers: 2 },
];

const sampleEvents = [
  {
    id: "EVT-8842",
    time: "Mar 14, 14:23",
    type: "shipment_delayed",
    detail: "delay_minutes=47, vendor=FastFreight",
    severity: "high",
  },
  {
    id: "EVT-8831",
    time: "Mar 14, 11:05",
    type: "shipment_delayed",
    detail: "delay_minutes=62, vendor=ExpressLogistics",
    severity: "critical",
  },
  {
    id: "EVT-8790",
    time: "Mar 12, 16:41",
    type: "shipment_delayed",
    detail: "delay_minutes=35, vendor=FastFreight",
    severity: "high",
  },
  {
    id: "EVT-8756",
    time: "Mar 10, 09:12",
    type: "shipment_delayed",
    detail: "delay_minutes=41, vendor=SwiftShip",
    severity: "high",
  },
  {
    id: "EVT-8721",
    time: "Mar 8, 22:30",
    type: "shipment_delayed",
    detail: "delay_minutes=88, vendor=ExpressLogistics",
    severity: "critical",
  },
  {
    id: "EVT-8699",
    time: "Mar 5, 07:58",
    type: "shipment_delayed",
    detail: "delay_minutes=33, vendor=CargoOne",
    severity: "high",
  },
];

const severityStyles: Record<string, string> = {
  critical: "bg-red-50 text-red-700",
  high: "bg-orange-50 text-orange-700",
  medium: "bg-yellow-50 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

export default function RuleSimulatePage() {
  const [expression, setExpression] = useState(
    'event.delay_minutes > 30 AND event.vendor_priority == "high"'
  );
  const [hasRun, setHasRun] = useState(false);

  const runSimulation = () => {
    setHasRun(true);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/rules"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Rule Simulation
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Test rules against historical data before activating
          </p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Rule Expression
        </h3>
        <textarea
          value={expression}
          onChange={(e) => setExpression(e.target.value)}
          rows={3}
          className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm font-mono bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal-400 resize-none"
          placeholder="Enter a rule expression..."
        />
        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={runSimulation}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            <Play className="w-4 h-4" /> Run Simulation (30 days)
          </button>
          <span className="text-xs text-gray-400">
            Evaluates against historical event data
          </span>
        </div>
      </div>

      {/* Results */}
      {hasRun && (
        <>
          {/* Summary */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center gap-3 mb-2">
              <Zap className="w-5 h-5 text-amber-500" />
              <h3 className="text-sm font-semibold text-gray-900">
                Simulation Results
              </h3>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              If this rule existed in the last 30 days, it would have triggered{" "}
              <span className="font-bold text-gray-900">23 times</span> across{" "}
              <span className="font-bold text-gray-900">4 vendors</span>.
            </p>

            {/* Chart */}
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 11, fill: "#94a3b8" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#94a3b8" }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: "1px solid #e2e8f0",
                    }}
                  />
                  <Bar
                    dataKey="triggers"
                    fill="#0d9488"
                    radius={[4, 4, 0, 0]}
                    name="Triggers"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Sample events table */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">
              Sample Triggered Events
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-gray-100">
                    <th className="pb-3 text-xs font-medium text-gray-400">
                      Event ID
                    </th>
                    <th className="pb-3 text-xs font-medium text-gray-400">
                      Time
                    </th>
                    <th className="pb-3 text-xs font-medium text-gray-400">
                      Type
                    </th>
                    <th className="pb-3 text-xs font-medium text-gray-400">
                      Detail
                    </th>
                    <th className="pb-3 text-xs font-medium text-gray-400">
                      Severity
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sampleEvents.map((evt) => (
                    <tr
                      key={evt.id}
                      className="border-b border-gray-50 hover:bg-gray-50"
                    >
                      <td className="py-3 font-mono text-xs text-gray-600">
                        {evt.id}
                      </td>
                      <td className="py-3 text-xs text-gray-500">{evt.time}</td>
                      <td className="py-3 text-xs text-gray-700">{evt.type}</td>
                      <td className="py-3 text-xs text-gray-500 font-mono">
                        {evt.detail}
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${severityStyles[evt.severity]}`}
                        >
                          {evt.severity}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Activate */}
          <div className="flex justify-end">
            <button className="px-6 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors">
              Activate Rule
            </button>
          </div>
        </>
      )}
    </div>
  );
}
