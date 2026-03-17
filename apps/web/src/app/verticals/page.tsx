"use client";

import { useState } from "react";
import { Truck, Heart, Factory, Thermometer, Check, ChevronDown, ChevronUp, UtensilsCrossed, ShoppingBag, ChefHat } from "lucide-react";

const verticals = [
  {
    name: "logistics",
    displayName: "Logistics & Transportation",
    description:
      "End-to-end logistics operations — shipment tracking, fleet management, vendor performance, and delivery SLA compliance.",
    icon: Truck,
    color: "text-blue-600",
    bg: "bg-blue-50",
    border: "border-blue-200",
    eventTypes: 12,
    ruleTemplates: 10,
    promptTemplates: 3,
    highlights: [
      "12 event types: shipment tracking, fleet, vendor, dock",
      "10 rules: delay alerts, SLA breach, driver idle, route deviation",
      "3 AI prompts: logistics query, shipment analysis, vendor evaluation",
      "Dashboard: on-time rate, active shipments, fleet utilisation",
    ],
  },
  {
    name: "healthcare",
    displayName: "Healthcare Operations",
    description:
      "Hospital and facility operations — patient flow, bed management, equipment tracking, compliance, and staff coordination.",
    icon: Heart,
    color: "text-rose-600",
    bg: "bg-rose-50",
    border: "border-rose-200",
    eventTypes: 10,
    ruleTemplates: 8,
    promptTemplates: 3,
    highlights: [
      "10 event types: patient flow, bed management, equipment, labs",
      "8 rules: capacity alerts, critical labs, compliance, response time",
      "3 AI prompts: healthcare query, patient flow, compliance report",
      "Dashboard: bed occupancy, wait times, compliance score",
    ],
  },
  {
    name: "manufacturing",
    displayName: "Manufacturing & Production",
    description:
      "Factory floor operations — production tracking, quality control, equipment health, material management, and shift coordination.",
    icon: Factory,
    color: "text-purple-600",
    bg: "bg-purple-50",
    border: "border-purple-200",
    eventTypes: 10,
    ruleTemplates: 8,
    promptTemplates: 3,
    highlights: [
      "10 event types: production, quality, equipment, materials, shifts",
      "8 rules: output targets, defect rates, equipment faults, OEE",
      "3 AI prompts: manufacturing query, production analysis, maintenance",
      "Dashboard: OEE score, production output, defect rate, uptime",
    ],
  },
  {
    name: "cold_chain",
    displayName: "Cold Chain & Temperature-Controlled",
    description:
      "Temperature-controlled supply chain — real-time sensor data, compliance tracking, excursion detection, and chain of custody.",
    icon: Thermometer,
    color: "text-cyan-600",
    bg: "bg-cyan-50",
    border: "border-cyan-200",
    eventTypes: 8,
    ruleTemplates: 8,
    promptTemplates: 3,
    highlights: [
      "8 event types: temperature, humidity, doors, excursions, custody",
      "8 rules: temp thresholds, excursion duration, calibration, compliance",
      "3 AI prompts: cold chain query, excursion analysis, compliance report",
      "Dashboard: compliance rate, excursions, avg temperature, sensors",
    ],
  },
  {
    name: "food_beverage",
    displayName: "Food & Beverage",
    description:
      "Food safety and quality operations — temperature monitoring, FSMA compliance, supplier quality, shelf life management, and waste tracking.",
    icon: UtensilsCrossed,
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
    eventTypes: 15,
    ruleTemplates: 12,
    promptTemplates: 3,
    highlights: [
      "15 event types: temperature, humidity, supplier, quality, contamination, waste",
      "12 rules: cold storage excursion, FSMA compliance, contamination, shelf life",
      "3 AI prompts: food safety query, supply chain analysis, compliance report",
      "Dashboard: active excursions, compliance score, waste rate, supplier on-time %",
    ],
  },
  {
    name: "merchandise_supply_chain",
    displayName: "Merchandise Supply Chain",
    description:
      "Global merchandise supply chain — container tracking, customs clearance, vendor management, inventory allocation, and demand planning.",
    icon: ShoppingBag,
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
    eventTypes: 15,
    ruleTemplates: 12,
    promptTemplates: 3,
    highlights: [
      "15 event types: containers, customs, vendor shipments, DC receiving, allocation",
      "12 rules: port dwell, customs hold, vendor reliability, stockout risk, seasonal deadline",
      "3 AI prompts: supply chain query, vendor evaluation, demand planning",
      "Dashboard: containers in transit, vendor on-time %, allocation completion, stockout risk",
    ],
  },
  {
    name: "restaurant_ops",
    displayName: "Restaurant Operations",
    description:
      "Multi-location restaurant operations — food safety, equipment monitoring, drive-thru performance, labor management, and health compliance.",
    icon: ChefHat,
    color: "text-orange-600",
    bg: "bg-orange-50",
    border: "border-orange-200",
    eventTypes: 15,
    ruleTemplates: 12,
    promptTemplates: 3,
    highlights: [
      "15 event types: cooler/freezer temps, fryer oil, drive-thru, POS, labor, complaints",
      "12 rules: cooler excursion, health inspection, drive-thru time, complaint spike",
      "3 AI prompts: restaurant ops query, location analysis, health compliance",
      "Dashboard: locations compliant, avg drive-thru time, food cost %, equipment uptime",
    ],
  },
];

export default function VerticalsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [applied, setApplied] = useState<Set<string>>(new Set());
  const [applying, setApplying] = useState<string | null>(null);

  const handleApply = (name: string) => {
    setApplying(name);
    setTimeout(() => {
      setApplying(null);
      setApplied((prev) => new Set([...prev, name]));
    }, 2000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Industry Verticals</h2>
        <p className="text-sm text-gray-500 mt-1">
          Pre-built packages with event types, rules, AI prompts, and dashboards for your industry
        </p>
      </div>

      {/* Vertical cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {verticals.map((v) => {
          const Icon = v.icon;
          const isExpanded = expanded === v.name;
          const isApplied = applied.has(v.name);
          const isApplying = applying === v.name;
          return (
            <div
              key={v.name}
              className={`bg-white rounded-xl border-2 transition-all ${
                isApplied ? `${v.border} shadow-md` : "border-gray-100 hover:border-gray-200"
              }`}
            >
              <div className="p-6">
                <div className="flex items-start gap-4">
                  <div className={`w-14 h-14 rounded-xl ${v.bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-7 h-7 ${v.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-gray-900 text-lg">{v.displayName}</h3>
                      {isApplied && (
                        <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
                          <Check className="w-3 h-3" /> Applied
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{v.description}</p>

                    {/* Stats */}
                    <div className="flex gap-4 mt-3">
                      <div className="text-center">
                        <span className="text-lg font-bold text-gray-900">{v.eventTypes}</span>
                        <p className="text-xs text-gray-400">Event Types</p>
                      </div>
                      <div className="text-center">
                        <span className="text-lg font-bold text-gray-900">{v.ruleTemplates}</span>
                        <p className="text-xs text-gray-400">Rules</p>
                      </div>
                      <div className="text-center">
                        <span className="text-lg font-bold text-gray-900">{v.promptTemplates}</span>
                        <p className="text-xs text-gray-400">AI Prompts</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expand / Apply */}
                <div className="flex items-center gap-3 mt-4">
                  <button
                    onClick={() => setExpanded(isExpanded ? null : v.name)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    {isExpanded ? "Hide Details" : "View Details"}
                  </button>
                  <button
                    onClick={() => handleApply(v.name)}
                    disabled={isApplied || isApplying}
                    className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isApplied
                        ? "bg-emerald-100 text-emerald-700 cursor-default"
                        : isApplying
                        ? "bg-gray-100 text-gray-400 cursor-wait"
                        : "bg-teal-600 text-white hover:bg-teal-700"
                    }`}
                  >
                    {isApplied ? (
                      <>
                        <Check className="w-3.5 h-3.5" /> Applied
                      </>
                    ) : isApplying ? (
                      "Applying..."
                    ) : (
                      "Apply Package"
                    )}
                  </button>
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      What will be configured
                    </h4>
                    <ul className="space-y-1.5">
                      {v.highlights.map((h, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                          <Check className="w-4 h-4 text-teal-500 flex-shrink-0 mt-0.5" />
                          {h}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
