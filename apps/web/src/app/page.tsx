import { KPICard } from "@/components/KPICard";
import { EventVolumeChart } from "@/components/EventVolumeChart";
import { AlertSeverityChart } from "@/components/AlertSeverityChart";
import { RecentAlerts } from "@/components/RecentAlerts";
import { SystemHealth } from "@/components/SystemHealth";

export default function Dashboard() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page heading */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">
          Overview for March 16, 2026
        </p>
      </div>

      {/* Row 1: KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Events Today"
          value="12,847"
          detail="+14.2% from yesterday"
          detailColor="green"
        />
        <KPICard
          label="Active Rules"
          value="156"
          detail="23 triggered today"
          detailColor="teal"
        />
        <KPICard
          label="Open Alerts"
          value="38"
          detail="12 critical"
          detailColor="red"
        />
        <KPICard
          label="AI Queries"
          value="284"
          detail="Avg 3.2s response"
          detailColor="gray"
        />
      </div>

      {/* Row 2: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <EventVolumeChart />
        <AlertSeverityChart />
      </div>

      {/* Row 3: Tables and panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <RecentAlerts />
        </div>
        <SystemHealth />
      </div>
    </div>
  );
}
