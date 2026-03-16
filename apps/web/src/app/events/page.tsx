import { Activity } from "lucide-react";

const events = [
  { id: "EVT-9847", type: "shipment_delayed", entity: "SHP-2024-089", source: "TMS", occurred: "2 min ago", payload: "Delay: 45 min — traffic on I-95" },
  { id: "EVT-9846", type: "delivery_completed", entity: "SHP-2024-085", source: "TMS", occurred: "8 min ago", payload: "Delivered to Warehouse B, signed by R. Chen" },
  { id: "EVT-9845", type: "driver_checkin", entity: "DRV-112", source: "Fleet App", occurred: "12 min ago", payload: "Check-in at Distribution Center East" },
  { id: "EVT-9844", type: "inventory_received", entity: "INV-3321", source: "WMS", occurred: "18 min ago", payload: "240 units received, PO-8891" },
  { id: "EVT-9843", type: "vehicle_status_changed", entity: "VEH-078", source: "IoT Gateway", occurred: "23 min ago", payload: "Status: maintenance_required — brake sensor alert" },
  { id: "EVT-9842", type: "route_deviated", entity: "RTE-445", source: "GPS Tracker", occurred: "31 min ago", payload: "Deviation: 4.2km from planned route" },
  { id: "EVT-9841", type: "vendor_delay", entity: "VND-019", source: "Supplier Portal", occurred: "38 min ago", payload: "Shipment from Vendor X delayed 2 hours" },
  { id: "EVT-9840", type: "order_created", entity: "ORD-7762", source: "ERP", occurred: "42 min ago", payload: "New order: 120 units to Nashville DC" },
  { id: "EVT-9839", type: "shipment_dispatched", entity: "SHP-2024-091", source: "TMS", occurred: "51 min ago", payload: "Dispatched via Route I-40 W, ETA 6h" },
  { id: "EVT-9838", type: "driver_checkin", entity: "DRV-098", source: "Fleet App", occurred: "1 hr ago", payload: "Check-in at Customer Site — Memphis" },
];

const typeColors: Record<string, string> = {
  shipment_delayed: "bg-red-50 text-red-700",
  delivery_completed: "bg-emerald-50 text-emerald-700",
  driver_checkin: "bg-blue-50 text-blue-700",
  inventory_received: "bg-purple-50 text-purple-700",
  vehicle_status_changed: "bg-amber-50 text-amber-700",
  route_deviated: "bg-orange-50 text-orange-700",
  vendor_delay: "bg-red-50 text-red-700",
  order_created: "bg-teal-50 text-teal-700",
  shipment_dispatched: "bg-emerald-50 text-emerald-700",
};

export default function EventsPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Events</h2>
          <p className="text-sm text-gray-500 mt-1">
            12,847 events ingested today
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-medium">
            <Activity className="w-3.5 h-3.5" />
            Live
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-teal-500">
          <option>All Event Types</option>
          <option>shipment_delayed</option>
          <option>delivery_completed</option>
          <option>driver_checkin</option>
          <option>inventory_received</option>
          <option>vehicle_status_changed</option>
          <option>route_deviated</option>
          <option>vendor_delay</option>
        </select>
        <select className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-teal-500">
          <option>All Sources</option>
          <option>TMS</option>
          <option>Fleet App</option>
          <option>WMS</option>
          <option>IoT Gateway</option>
          <option>GPS Tracker</option>
          <option>ERP</option>
        </select>
        <input
          type="text"
          placeholder="Search events..."
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-teal-500 w-64"
        />
      </div>

      {/* Events table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3">Event ID</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3">Type</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3">Entity</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3">Source</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3">Details</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {events.map((event) => (
              <tr key={event.id} className="hover:bg-gray-50/50 transition-colors">
                <td className="px-6 py-4 text-sm font-mono text-gray-600">{event.id}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2.5 py-1 rounded-md text-xs font-medium ${typeColors[event.type] || "bg-gray-50 text-gray-700"}`}>
                    {event.type}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{event.entity}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{event.source}</td>
                <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">{event.payload}</td>
                <td className="px-6 py-4 text-sm text-gray-400 text-right whitespace-nowrap">{event.occurred}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
