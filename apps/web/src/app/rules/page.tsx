const rules = [
  { id: "RUL-001", name: "Late Shipment Alert", type: "event_triggered", trigger: "shipment_delayed", expression: "event.delay_minutes > 30 AND event.vendor_priority == \"high\"", severity: "critical", enabled: true, triggered: 12 },
  { id: "RUL-002", name: "Temperature Threshold", type: "threshold", trigger: "temperature_reading", expression: "avg(temperature) > 85 FOR 10m", severity: "high", enabled: true, triggered: 3 },
  { id: "RUL-003", name: "Multi-Vendor Failure", type: "composite", trigger: "vendor_delay + shipment_delayed", expression: "3x vendor_delay AND shipment_delayed AND inventory_risk WITHIN 2h", severity: "critical", enabled: true, triggered: 1 },
  { id: "RUL-004", name: "Route Deviation Alert", type: "event_triggered", trigger: "route_deviated", expression: "event.deviation_km > 3.0", severity: "medium", enabled: true, triggered: 8 },
  { id: "RUL-005", name: "Driver Idle Time", type: "threshold", trigger: "driver_checkin", expression: "time_since_last_checkin > 4h", severity: "medium", enabled: true, triggered: 5 },
  { id: "RUL-006", name: "Inventory Low Stock", type: "threshold", trigger: "inventory_received", expression: "stock_level < reorder_point FOR 30m", severity: "high", enabled: false, triggered: 0 },
  { id: "RUL-007", name: "Delivery SLA Breach", type: "event_triggered", trigger: "delivery_completed", expression: "event.actual_time > event.promised_time + 60m", severity: "high", enabled: true, triggered: 6 },
  { id: "RUL-008", name: "Fleet Maintenance Due", type: "composite", trigger: "vehicle_status_changed", expression: "maintenance_alert AND mileage > threshold AND age > 3y", severity: "low", enabled: true, triggered: 2 },
];

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

export default function RulesPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Rules</h2>
          <p className="text-sm text-gray-500 mt-1">
            156 active rules &middot; 23 triggered today
          </p>
        </div>
        <button className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors">
          Create Rule
        </button>
      </div>

      {/* Rules grid */}
      <div className="grid gap-4">
        {rules.map((rule) => (
          <div key={rule.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-sm font-semibold text-gray-900">{rule.name}</h3>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${typeStyles[rule.type]}`}>
                    {rule.type.replace("_", " ")}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${severityStyles[rule.severity]}`}>
                    {rule.severity}
                  </span>
                </div>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs text-gray-400 font-mono">{rule.id}</span>
                  <span className="text-gray-300">&middot;</span>
                  <span className="text-xs text-gray-500">Trigger: {rule.trigger}</span>
                </div>
                <code className="block text-xs bg-gray-50 text-gray-700 px-3 py-2 rounded-lg font-mono">
                  {rule.expression}
                </code>
              </div>
              <div className="flex items-center gap-4 ml-6">
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900">{rule.triggered}</p>
                  <p className="text-xs text-gray-400">triggered today</p>
                </div>
                <div className={`w-10 h-6 rounded-full flex items-center px-1 transition-colors ${rule.enabled ? "bg-teal-500 justify-end" : "bg-gray-300 justify-start"}`}>
                  <div className="w-4 h-4 rounded-full bg-white shadow" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
