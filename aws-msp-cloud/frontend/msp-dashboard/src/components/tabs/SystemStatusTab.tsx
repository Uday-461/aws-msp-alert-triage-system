import { ServiceHealthGrid } from '@/components/status/ServiceHealthGrid';
import { MLModelsTable } from '@/components/status/MLModelsTable';
import { DatabaseStats } from '@/components/status/DatabaseStats';

export function SystemStatusTab() {
  return (
    <div className="space-y-8">
      {/* Service Health */}
      <ServiceHealthGrid />

      {/* ML Models Performance */}
      <MLModelsTable />

      {/* Database Statistics */}
      <DatabaseStats />
    </div>
  );
}
