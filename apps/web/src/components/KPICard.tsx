import clsx from "clsx";

interface KPICardProps {
  label: string;
  value: string;
  detail: string;
  detailColor?: "green" | "red" | "gray" | "teal";
}

const colorMap = {
  green: "text-emerald-600",
  red: "text-red-500",
  gray: "text-gray-500",
  teal: "text-teal-600",
};

export function KPICard({ label, value, detail, detailColor = "gray" }: KPICardProps) {
  return (
    <div className="card card-hover">
      <p className="text-sm font-medium text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900 tracking-tight">{value}</p>
      <p className={clsx("text-sm mt-2", colorMap[detailColor])}>{detail}</p>
    </div>
  );
}
