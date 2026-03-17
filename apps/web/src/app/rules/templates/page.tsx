"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";

const typeStyles: Record<string, string> = {
  event_triggered: "bg-blue-50 text-blue-700",
  threshold: "bg-purple-50 text-purple-700",
  composite: "bg-amber-50 text-amber-700",
};

const severityStyles: Record<string, string> = {
  critical: "bg-red-50 text-red-700",
  high: "bg-orange-50 text-orange-700",
  medium: "bg-yellow-50 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

const templates = [
  {
    id: "tpl-001",
    name: "Late Shipment Alert",
    type: "event_triggered",
    severity: "high",
    description:
      "Triggers when a shipment is delayed by more than 30 minutes. Useful for monitoring carrier SLAs and proactively notifying customers.",
    expression: 'event.delay_minutes > 30 AND event.vendor_priority == "high"',
  },
  {
    id: "tpl-002",
    name: "Driver Idle Warning",
    type: "threshold",
    severity: "medium",
    description:
      "Alerts when a driver has not checked in for over 4 hours. Helps fleet managers identify potential issues or rest-stop violations.",
    expression: "event.idle_hours > 4 FOR 30m",
  },
  {
    id: "tpl-003",
    name: "Temperature Excursion",
    type: "threshold",
    severity: "critical",
    description:
      "Fires when temperature readings exceed 85 degrees Fahrenheit for 10 consecutive minutes. Critical for cold-chain compliance.",
    expression: "event.temperature > 85 FOR 10m",
  },
  {
    id: "tpl-004",
    name: "Inventory Low Stock",
    type: "threshold",
    severity: "high",
    description:
      "Triggers when stock level falls below the reorder point. Prevents stockouts by alerting procurement teams early.",
    expression: "event.stock_level < reorder_point FOR 30m",
  },
  {
    id: "tpl-005",
    name: "Route Deviation",
    type: "event_triggered",
    severity: "medium",
    description:
      "Alerts when a vehicle deviates more than 3 kilometers from the planned route. Helps detect unauthorized stops or wrong turns.",
    expression: "event.deviation_km > 3.0",
  },
  {
    id: "tpl-006",
    name: "Vendor Delay Pattern",
    type: "composite",
    severity: "high",
    description:
      "Identifies vendors with 3 or more delays within a 7-day window. Useful for vendor performance reviews and contract negotiations.",
    expression: "3x vendor_delay WITHIN 7d",
  },
  {
    id: "tpl-007",
    name: "Delivery SLA Breach",
    type: "event_triggered",
    severity: "high",
    description:
      "Fires when actual delivery time exceeds promised time by more than 60 minutes. Tracks service quality and customer satisfaction.",
    expression: "event.actual_time > event.promised_time + 60m",
  },
  {
    id: "tpl-008",
    name: "Fleet Maintenance Due",
    type: "composite",
    severity: "low",
    description:
      "Triggers when vehicle mileage exceeds the maintenance threshold. Ensures preventive maintenance schedules are followed.",
    expression: "event.mileage > threshold AND maintenance_alert",
  },
];

export default function RuleTemplatesPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/rules"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Rule Templates
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Pre-built rules you can customize and deploy instantly
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {templates.map((tpl) => (
          <div
            key={tpl.id}
            className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow flex flex-col"
          >
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-sm font-semibold text-gray-900">
                {tpl.name}
              </h3>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${typeStyles[tpl.type]}`}
              >
                {tpl.type.replace("_", " ")}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${severityStyles[tpl.severity]}`}
              >
                {tpl.severity}
              </span>
            </div>
            <p className="text-xs text-gray-500 mb-4 flex-1 leading-relaxed">
              {tpl.description}
            </p>
            <code className="block text-xs bg-gray-50 text-gray-700 px-3 py-2 rounded-lg font-mono mb-4">
              {tpl.expression}
            </code>
            <Link
              href="/rules/builder"
              className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              Use Template <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
