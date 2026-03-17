"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Radio, AlertTriangle, X } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LiveEvent {
  id: string;
  event_type: string;
  timestamp: string;
  vendor: string;
  detail: string;
}

interface LiveAlert {
  id: string;
  title: string;
  severity: string;
  timestamp: string;
  message: string;
  visible: boolean;
}

interface KPI {
  events_today: number;
  active_rules: number;
  open_alerts: number;
  ai_queries: number;
}

// ---------------------------------------------------------------------------
// Mock data generators
// ---------------------------------------------------------------------------

const EVENT_TYPES = [
  "shipment_delayed",
  "temperature_reading",
  "driver_checkin",
  "route_deviated",
  "inventory_received",
  "delivery_completed",
  "vehicle_status_changed",
  "vendor_delay",
];

const VENDORS = [
  "FastFreight",
  "ExpressLogistics",
  "SwiftShip",
  "CargoOne",
  "PrimeHaul",
];

const DETAILS: Record<string, () => string> = {
  shipment_delayed: () => `delay=${Math.floor(Math.random() * 90 + 10)}min`,
  temperature_reading: () => `temp=${(Math.random() * 60 + 40).toFixed(1)}F`,
  driver_checkin: () => `driver=M. Chen, loc=I-95 North`,
  route_deviated: () => `deviation=${(Math.random() * 10 + 1).toFixed(1)}km`,
  inventory_received: () => `qty=${Math.floor(Math.random() * 500 + 50)}`,
  delivery_completed: () => `on_time=${Math.random() > 0.3 ? "yes" : "no"}`,
  vehicle_status_changed: () => `status=maintenance_due`,
  vendor_delay: () => `vendor=${VENDORS[Math.floor(Math.random() * VENDORS.length)]}`,
};

const ALERT_TITLES = [
  "Late Shipment Alert",
  "Temperature Excursion",
  "Route Deviation Detected",
  "Driver Idle Warning",
  "Vendor Delay Pattern",
  "Delivery SLA Breach",
];

const eventTypeColors: Record<string, string> = {
  shipment_delayed: "border-l-orange-400 bg-orange-50/50",
  temperature_reading: "border-l-red-400 bg-red-50/50",
  driver_checkin: "border-l-blue-400 bg-blue-50/50",
  route_deviated: "border-l-amber-400 bg-amber-50/50",
  inventory_received: "border-l-green-400 bg-green-50/50",
  delivery_completed: "border-l-teal-400 bg-teal-50/50",
  vehicle_status_changed: "border-l-purple-400 bg-purple-50/50",
  vendor_delay: "border-l-rose-400 bg-rose-50/50",
};

const severityColors: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-gray-400",
};

let idCounter = 1000;
function nextId(prefix: string) {
  return `${prefix}-${++idCounter}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LiveOpsPage() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [alerts, setAlerts] = useState<LiveAlert[]>([]);
  const [popupAlerts, setPopupAlerts] = useState<LiveAlert[]>([]);
  const [kpi, setKpi] = useState<KPI>({
    events_today: 12847,
    active_rules: 156,
    open_alerts: 38,
    ai_queries: 284,
  });
  const [paused, setPaused] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(false);

  // Keep ref in sync
  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  // Generate mock events
  useEffect(() => {
    const interval = setInterval(() => {
      if (pausedRef.current) return;

      const etype =
        EVENT_TYPES[Math.floor(Math.random() * EVENT_TYPES.length)];
      const evt: LiveEvent = {
        id: nextId("EVT"),
        event_type: etype,
        timestamp: new Date().toLocaleTimeString(),
        vendor: VENDORS[Math.floor(Math.random() * VENDORS.length)],
        detail: DETAILS[etype](),
      };
      setEvents((prev) => [evt, ...prev].slice(0, 100));

      // KPI tick
      setKpi((prev) => ({
        ...prev,
        events_today: prev.events_today + 1,
        ai_queries: prev.ai_queries + (Math.random() > 0.7 ? 1 : 0),
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Generate mock alerts
  useEffect(() => {
    const interval = setInterval(() => {
      if (pausedRef.current) return;
      if (Math.random() > 0.4) return;

      const sev = ["low", "medium", "high", "critical"][
        Math.floor(Math.random() * 4)
      ];
      const a: LiveAlert = {
        id: nextId("ALR"),
        title: ALERT_TITLES[Math.floor(Math.random() * ALERT_TITLES.length)],
        severity: sev,
        timestamp: new Date().toLocaleTimeString(),
        message: "Triggered by rule engine",
        visible: true,
      };
      setAlerts((prev) => [a, ...prev].slice(0, 50));

      // Popup for critical/high
      if (sev === "critical" || sev === "high") {
        setPopupAlerts((prev) => [a, ...prev].slice(0, 3));
        setKpi((prev) => ({ ...prev, open_alerts: prev.open_alerts + 1 }));
        // Auto dismiss after 5 seconds
        setTimeout(() => {
          setPopupAlerts((prev) => prev.filter((p) => p.id !== a.id));
        }, 5000);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const dismissPopup = useCallback((id: string) => {
    setPopupAlerts((prev) => prev.filter((p) => p.id !== id));
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6 relative">
      {/* Popup alerts - slide in from right */}
      <div className="fixed top-20 right-6 z-50 space-y-2 w-80">
        {popupAlerts.map((a) => (
          <div
            key={a.id}
            className="bg-white rounded-xl shadow-lg border border-gray-200 p-4 animate-slide-in"
            style={{
              animation: "slideIn 0.3s ease-out",
            }}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle
                  className={`w-4 h-4 ${
                    a.severity === "critical"
                      ? "text-red-500"
                      : "text-orange-500"
                  }`}
                />
                <span className="text-sm font-semibold text-gray-900">
                  {a.title}
                </span>
              </div>
              <button
                onClick={() => dismissPopup(a.id)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">{a.message}</p>
            <div className="flex items-center gap-2 mt-2">
              <span
                className={`w-2 h-2 rounded-full ${severityColors[a.severity]}`}
              />
              <span className="text-xs text-gray-400">
                {a.severity} &middot; {a.timestamp}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Radio className="w-5 h-5 text-teal-600" />
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Live Operations Center
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">
              Real-time event stream and alert monitoring
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                paused ? "bg-yellow-400" : "bg-emerald-400"
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                paused ? "bg-yellow-500" : "bg-emerald-500"
              }`}
            />
          </span>
          <span className="text-sm text-gray-500">
            {paused ? "Paused" : "Live"}
          </span>
          <button
            onClick={() => setPaused(!paused)}
            className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
          >
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Events Today",
            value: kpi.events_today.toLocaleString(),
            color: "text-teal-600",
          },
          {
            label: "Active Rules",
            value: kpi.active_rules.toString(),
            color: "text-blue-600",
          },
          {
            label: "Open Alerts",
            value: kpi.open_alerts.toString(),
            color: "text-orange-600",
          },
          {
            label: "AI Queries",
            value: kpi.ai_queries.toString(),
            color: "text-purple-600",
          },
        ].map((k) => (
          <div
            key={k.label}
            className="bg-white rounded-xl shadow-sm border border-gray-100 p-4"
          >
            <p className="text-xs text-gray-400 mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Event feed — left 2/3 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900">
                Live Event Feed
              </h3>
            </div>
            <div
              ref={feedRef}
              className="max-h-[500px] overflow-y-auto divide-y divide-gray-50"
              onMouseEnter={() => setPaused(true)}
              onMouseLeave={() => setPaused(false)}
            >
              {events.length === 0 && (
                <div className="p-8 text-center text-sm text-gray-400">
                  Waiting for events...
                </div>
              )}
              {events.map((evt) => (
                <div
                  key={evt.id}
                  className={`px-6 py-3 border-l-4 ${
                    eventTypeColors[evt.event_type] || "border-l-gray-300"
                  }`}
                  style={{ animation: "fadeIn 0.4s ease-out" }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-gray-400">
                        {evt.id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                        {evt.event_type.replace("_", " ")}
                      </span>
                      <span className="text-xs text-gray-500">
                        {evt.vendor}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {evt.timestamp}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 font-mono mt-1">
                    {evt.detail}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Alert feed — right 1/3 */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900">
                Alert Feed
              </h3>
            </div>
            <div className="max-h-[500px] overflow-y-auto divide-y divide-gray-50">
              {alerts.length === 0 && (
                <div className="p-8 text-center text-sm text-gray-400">
                  No alerts yet
                </div>
              )}
              {alerts.map((a) => (
                <div
                  key={a.id}
                  className="px-4 py-3"
                  style={{ animation: "fadeIn 0.4s ease-out" }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        severityColors[a.severity]
                      }`}
                    />
                    <span className="text-xs font-semibold text-gray-900 truncate">
                      {a.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 ml-4">
                    <span className="text-xs text-gray-400">{a.severity}</span>
                    <span className="text-gray-300">&middot;</span>
                    <span className="text-xs text-gray-400">{a.timestamp}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Inline styles for animations */}
      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(100px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}
