import { DashboardGreeting } from "./DashboardGreeting";
import { DashboardStats } from "./DashboardStats";
import { DashboardAgenda } from "./DashboardAgenda";
import { DashboardActivities } from "./DashboardActivities";
import { DashboardShortcuts } from "./DashboardShortcuts";
import { DashboardChart } from "./DashboardChart";

export function DashboardView() {
  return (
    <div className="p-8">
      <div className="space-y-8">
        <DashboardGreeting />

        <DashboardStats />

        <div className="grid gap-5 xl:grid-cols-[1.4fr_0.9fr]">
          <DashboardAgenda />
          <DashboardActivities />
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <DashboardChart />
          <DashboardShortcuts />
        </div>
      </div>
    </div>
  );
}
