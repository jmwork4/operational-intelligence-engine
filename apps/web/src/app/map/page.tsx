"use client";

import { useState } from "react";
import { MapPin } from "lucide-react";

// ---------------------------------------------------------------------------
// Mock entities with approximate US map positions (% based)
// ---------------------------------------------------------------------------

interface Entity {
  id: string;
  name: string;
  type: "vehicle" | "shipment";
  status: "on_time" | "delayed" | "critical";
  location: string;
  x: number; // % from left
  y: number; // % from top
  detail: string;
}

const entities: Entity[] = [
  {
    id: "VEH-101",
    name: "Truck Alpha",
    type: "vehicle",
    status: "on_time",
    location: "Chicago, IL",
    x: 58,
    y: 32,
    detail: "ETA 2:30 PM — On schedule",
  },
  {
    id: "VEH-102",
    name: "Truck Bravo",
    type: "vehicle",
    status: "delayed",
    location: "Dallas, TX",
    x: 47,
    y: 62,
    detail: "Delayed 22 min — Traffic on I-35",
  },
  {
    id: "SHP-201",
    name: "Shipment #4021",
    type: "shipment",
    status: "on_time",
    location: "Atlanta, GA",
    x: 67,
    y: 55,
    detail: "In transit — FastFreight",
  },
  {
    id: "VEH-103",
    name: "Truck Charlie",
    type: "vehicle",
    status: "critical",
    location: "Phoenix, AZ",
    x: 22,
    y: 58,
    detail: "Temperature excursion — 92F",
  },
  {
    id: "SHP-202",
    name: "Shipment #4035",
    type: "shipment",
    status: "on_time",
    location: "Seattle, WA",
    x: 14,
    y: 14,
    detail: "Delivered — SwiftShip",
  },
  {
    id: "VEH-104",
    name: "Truck Delta",
    type: "vehicle",
    status: "delayed",
    location: "Denver, CO",
    x: 33,
    y: 40,
    detail: "Delayed 45 min — Maintenance stop",
  },
  {
    id: "SHP-203",
    name: "Shipment #4042",
    type: "shipment",
    status: "critical",
    location: "Miami, FL",
    x: 73,
    y: 78,
    detail: "SLA breach — 67 min late",
  },
  {
    id: "VEH-105",
    name: "Truck Echo",
    type: "vehicle",
    status: "on_time",
    location: "New York, NY",
    x: 80,
    y: 30,
    detail: "ETA 4:15 PM — On schedule",
  },
  {
    id: "SHP-204",
    name: "Shipment #4058",
    type: "shipment",
    status: "on_time",
    location: "Minneapolis, MN",
    x: 50,
    y: 22,
    detail: "In transit — CargoOne",
  },
  {
    id: "VEH-106",
    name: "Truck Foxtrot",
    type: "vehicle",
    status: "delayed",
    location: "Los Angeles, CA",
    x: 12,
    y: 52,
    detail: "Delayed 15 min — Route deviation",
  },
];

const statusColors: Record<string, string> = {
  on_time: "bg-emerald-500",
  delayed: "bg-yellow-500",
  critical: "bg-red-500",
};

const statusLabels: Record<string, string> = {
  on_time: "On Time",
  delayed: "Delayed",
  critical: "Critical",
};

const statusBadgeStyles: Record<string, string> = {
  on_time: "bg-emerald-50 text-emerald-700",
  delayed: "bg-yellow-50 text-yellow-700",
  critical: "bg-red-50 text-red-700",
};

export default function MapPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const counts = {
    on_time: entities.filter((e) => e.status === "on_time").length,
    delayed: entities.filter((e) => e.status === "delayed").length,
    critical: entities.filter((e) => e.status === "critical").length,
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <MapPin className="w-5 h-5 text-teal-600" />
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Fleet & Shipment Map
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Real-time locations of vehicles and shipments
          </p>
        </div>
      </div>

      {/* Status legend */}
      <div className="flex items-center gap-6">
        {(["on_time", "delayed", "critical"] as const).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${statusColors[s]}`} />
            <span className="text-sm text-gray-600">
              {statusLabels[s]} ({counts[s]})
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map area — left 2/3 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            {/* Stylized US map using SVG */}
            <div className="relative w-full" style={{ paddingBottom: "60%" }}>
              <svg
                viewBox="0 0 960 600"
                className="absolute inset-0 w-full h-full"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Simplified US outline */}
                <path
                  d="M120,80 L200,70 L280,75 L340,80 L400,70 L460,65 L520,80 L580,75 L640,85 L700,80 L750,90 L800,100 L830,120 L840,160 L850,200 L845,240 L830,280 L810,310 L780,340 L750,360 L730,380 L710,400 L690,420 L660,440 L630,460 L600,470 L560,475 L520,480 L480,485 L440,480 L400,470 L360,460 L320,450 L280,430 L250,410 L220,390 L190,370 L160,350 L140,320 L130,290 L120,260 L110,230 L105,200 L100,170 L105,140 L110,110 Z"
                  fill="#f8fafc"
                  stroke="#e2e8f0"
                  strokeWidth="2"
                />
                {/* State dividers (simplified) */}
                <line x1="480" y1="70" x2="480" y2="480" stroke="#f1f5f9" strokeWidth="1" />
                <line x1="350" y1="100" x2="350" y2="460" stroke="#f1f5f9" strokeWidth="1" />
                <line x1="620" y1="80" x2="620" y2="470" stroke="#f1f5f9" strokeWidth="1" />
                <line x1="100" y1="200" x2="850" y2="200" stroke="#f1f5f9" strokeWidth="1" />
                <line x1="100" y1="340" x2="780" y2="340" stroke="#f1f5f9" strokeWidth="1" />

                {/* Entity dots */}
                {entities.map((entity) => {
                  const cx = (entity.x / 100) * 960;
                  const cy = (entity.y / 100) * 600;
                  const fill =
                    entity.status === "on_time"
                      ? "#10b981"
                      : entity.status === "delayed"
                      ? "#eab308"
                      : "#ef4444";
                  const isSelected = selected === entity.id;
                  return (
                    <g key={entity.id}>
                      {/* Pulse ring for critical */}
                      {entity.status === "critical" && (
                        <circle
                          cx={cx}
                          cy={cy}
                          r="18"
                          fill="none"
                          stroke="#ef4444"
                          strokeWidth="2"
                          opacity="0.3"
                        >
                          <animate
                            attributeName="r"
                            from="10"
                            to="24"
                            dur="1.5s"
                            repeatCount="indefinite"
                          />
                          <animate
                            attributeName="opacity"
                            from="0.4"
                            to="0"
                            dur="1.5s"
                            repeatCount="indefinite"
                          />
                        </circle>
                      )}
                      {/* Main dot */}
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isSelected ? 12 : 8}
                        fill={fill}
                        stroke="white"
                        strokeWidth="3"
                        className="cursor-pointer transition-all"
                        onClick={() =>
                          setSelected(
                            selected === entity.id ? null : entity.id
                          )
                        }
                      />
                      {/* Label */}
                      {isSelected && (
                        <g>
                          <rect
                            x={cx - 60}
                            y={cy - 40}
                            width="120"
                            height="28"
                            rx="6"
                            fill="white"
                            stroke="#e2e8f0"
                            strokeWidth="1"
                          />
                          <text
                            x={cx}
                            y={cy - 22}
                            textAnchor="middle"
                            fontSize="11"
                            fontWeight="600"
                            fill="#1e293b"
                          >
                            {entity.name}
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>
        </div>

        {/* Side panel — right 1/3 */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900">
                Fleet Overview
              </h3>
            </div>
            <div className="max-h-[500px] overflow-y-auto divide-y divide-gray-50">
              {entities.map((entity) => (
                <button
                  key={entity.id}
                  onClick={() =>
                    setSelected(selected === entity.id ? null : entity.id)
                  }
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                    selected === entity.id ? "bg-teal-50/50" : ""
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900">
                      {entity.name}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        statusBadgeStyles[entity.status]
                      }`}
                    >
                      {statusLabels[entity.status]}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{entity.location}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {entity.detail}
                  </p>
                  <span className="text-xs text-gray-300 font-mono">
                    {entity.id}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
