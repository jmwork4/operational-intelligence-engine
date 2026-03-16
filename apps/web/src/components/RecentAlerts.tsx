import clsx from "clsx";

interface Alert {
  time: string;
  entity: string;
  severity: "Critical" | "High" | "Medium" | "Low";
  status: "Open" | "Acknowledged" | "Investigating";
  message: string;
}

const alerts: Alert[] = [
  {
    time: "14:32",
    entity: "SHP-2024-089",
    severity: "Critical",
    status: "Investigating",
    message: "Shipment delayed 45 min past SLA threshold",
  },
  {
    time: "14:18",
    entity: "V-112",
    severity: "High",
    status: "Open",
    message: "Vehicle route deviation detected - 12km off path",
  },
  {
    time: "13:55",
    entity: "WH-North-03",
    severity: "Medium",
    status: "Acknowledged",
    message: "Warehouse capacity at 92% - approaching limit",
  },
  {
    time: "13:41",
    entity: "DRV-0447",
    severity: "Critical",
    status: "Open",
    message: "Driver hours exceed regulatory limit by 30 min",
  },
  {
    time: "13:22",
    entity: "SHP-2024-102",
    severity: "Low",
    status: "Open",
    message: "Customs documentation pending review",
  },
  {
    time: "12:58",
    entity: "V-089",
    severity: "High",
    status: "Investigating",
    message: "Engine diagnostic fault code reported",
  },
];

const severityStyles = {
  Critical: "bg-red-50 text-red-700 ring-red-600/20",
  High: "bg-orange-50 text-orange-700 ring-orange-600/20",
  Medium: "bg-yellow-50 text-yellow-700 ring-yellow-600/20",
  Low: "bg-gray-50 text-gray-600 ring-gray-500/20",
};

export function RecentAlerts() {
  return (
    <div className="card card-hover">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Recent Alerts</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Time
              </th>
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entity
              </th>
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Severity
              </th>
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="text-left py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                Message
              </th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, i) => (
              <tr
                key={i}
                className="border-b border-gray-50 last:border-0"
              >
                <td className="py-3 pr-4 text-gray-500 font-mono text-xs">
                  {alert.time}
                </td>
                <td className="py-3 pr-4 font-medium text-gray-900">
                  {alert.entity}
                </td>
                <td className="py-3 pr-4">
                  <span
                    className={clsx(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
                      severityStyles[alert.severity]
                    )}
                  >
                    {alert.severity}
                  </span>
                </td>
                <td className="py-3 pr-4 text-gray-600">{alert.status}</td>
                <td className="py-3 text-gray-600 max-w-xs truncate">
                  {alert.message}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
