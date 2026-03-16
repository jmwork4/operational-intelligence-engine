interface HealthItem {
  name: string;
  status: "healthy" | "degraded" | "down";
  detail: string;
}

const items: HealthItem[] = [
  { name: "API", status: "healthy", detail: "99.9% uptime" },
  { name: "Workers", status: "healthy", detail: "5 active" },
  { name: "Database", status: "healthy", detail: "28/100 connections" },
  { name: "Redis", status: "healthy", detail: "Healthy" },
  { name: "Storage", status: "healthy", detail: "2.4 GB used" },
];

const statusDot = {
  healthy: "bg-emerald-500",
  degraded: "bg-yellow-500",
  down: "bg-red-500",
};

export function SystemHealth() {
  return (
    <div className="card card-hover">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">System Health</h3>
      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.name} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`w-2 h-2 rounded-full ${statusDot[item.status]}`} />
              <span className="text-sm font-medium text-gray-900">{item.name}</span>
            </div>
            <span className="text-sm text-gray-500">{item.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
