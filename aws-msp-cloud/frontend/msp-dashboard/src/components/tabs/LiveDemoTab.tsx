import { MetricsCards } from '@/components/MetricsCards';
import { PipelineView } from '@/components/PipelineView';
import { DemoControls } from '@/components/demo/DemoControls';
import { AnimatedPipeline } from '@/components/demo/AnimatedPipeline';
import { LiveAlertFeed } from '@/components/demo/LiveAlertFeed';
import { AlertList } from '@/components/AlertList';

export function LiveDemoTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold">Live Demo</h2>
        <p className="text-muted-foreground mt-1">
          Real-time alert processing and ML pipeline visualization
        </p>
      </div>

      {/* Demo Controls */}
      <DemoControls />

      {/* Animated Alert Flow */}
      <AnimatedPipeline />

      {/* Real-time Metrics */}
      <MetricsCards />

      {/* Live Alert Feed & Alert List Side-by-Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Alert Feed (left) */}
        <LiveAlertFeed />

        {/* Pipeline Visualization (right) */}
        <PipelineView />
      </div>

      {/* Full Alert Management Table */}
      <AlertList />
    </div>
  );
}
