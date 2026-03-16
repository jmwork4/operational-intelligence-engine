import { Bell } from "lucide-react";

const alerts = [
  { id: "ALR-482", rule: "Late Shipment Alert", entity: "SHP-2024-089", severity: "critical", status: "active", message: "Shipment delayed 45 min on I-95, vendor priority high", time: "2 min ago" },
  { id: "ALR-481", rule: "Route Deviation Alert", entity: "RTE-445", severity: "medium", status: "active", message: "4.2km deviation from planned route — DRV-067", time: "31 min ago" },
  { id: "ALR-480", rule: "Multi-Vendor Failure", entity: "VND-019", severity: "critical", status: "active", message: "3rd vendor delay this week, correlated with inventory risk", time: "38 min ago" },
  { id: "ALR-479", rule: "Temperature Threshold", entity: "WH-East-04", severity: "high", status: "acknowledged", message: "Cold storage unit 4 at 88°F for 12 minutes", time: "1 hr ago" },
  { id: "ALR-478", rule: "Delivery SLA Breach", entity: "SHP-2024-082", severity: "high", status: "acknowledged", message: "Delivery exceeded promised window by 74 minutes", time: "2 hr ago" },
  { id: "ALR-477", rule: "Driver Idle Time", entity: "DRV-045", severity: "medium", status: "resolved", message: "No check-in for 5.2 hours — driver confirmed break", time: "3 hr ago" },
  { id: "ALR-476", rule: "Fleet Maintenance Due", entity: "VEH-078", severity: "low", status: "resolved", message: "Brake sensor alert — maintenance scheduled for tomorrow", time: "4 hr ago" },
  { id: "ALR-475", rule: "Late Shipment Alert", entity: "SHP-2024-076", severity: "critical", status: "resolved", message: "Shipment delayed 62 min — rerouted successfully", time: "5 hr ago" },
];

const severityStyles: Record<string, string> = {
  critical: "bg-red-50 text-red-700 border-red-100",
  high: "bg-orange-50 text-orange-700 border-orange-100",
  medium: "bg-yellow-50 text-yellow-700 border-yellow-100",
  low: "bg-gray-50 text-gray-600 border-gray-100",
};

const statusStyles: Record<string, string> = {
  active: "bg-red-500",
  acknowledged: "bg-amber-500",
  resolved: "bg-emerald-500",
};

export default function AlertsPage() {
  const criticalCount = alerts.filter((a) => a.severity === "critical" && a.status === "active").length;
  const activeCount = alerts.filter((a) => a.status === "active").length;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Alerts</h2>
          <p className="text-sm text-gray-500 mt-1">
            {activeCount} active &middot; {criticalCount} critical requiring attention
          </p>
        </div>
        <div className="flex gap-2">
          {["All", "Active", "Acknowledged", "Resolved"].map((filter) => (
            <button
              key={filter}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                filter === "All"
                  ? "bg-teal-600 text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Alert cards */}
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition-shadow ${
              alert.status === "active" && alert.severity === "critical"
                ? "border-red-200 border-l-4 border-l-red-500"
                : "border-gray-100"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${statusStyles[alert.status]}`} />
                    <span className="text-xs font-medium text-gray-400 uppercase">{alert.status}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${severityStyles[alert.severity]}`}>
                    {alert.severity}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{alert.id}</span>
                </div>
                <p className="text-sm font-medium text-gray-900 mb-1">{alert.message}</p>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span>Rule: {alert.rule}</span>
                  <span>&middot;</span>
                  <span>Entity: {alert.entity}</span>
                  <span>&middot;</span>
                  <span>{alert.time}</span>
                </div>
              </div>
              {alert.status === "active" && (
                <div className="flex gap-2 ml-4">
                  <button className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors">
                    Acknowledge
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors">
                    Resolve
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
