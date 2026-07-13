import { MetricCard } from "@/components/ui/MetricCard";

type StatCardProps = {
  title: string;
  value: string;
  description: string;
};

export function StatCard({
  title,
  value,
  description,
}: StatCardProps) {
  return <MetricCard title={title} value={value} description={description} />;
}
