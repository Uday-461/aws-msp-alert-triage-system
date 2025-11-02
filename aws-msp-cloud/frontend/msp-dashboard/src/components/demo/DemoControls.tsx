import { useState } from 'react';
import { useDemo } from '@/hooks/useDemo';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Play, Pause, RotateCcw, Loader2 } from 'lucide-react';

export function DemoControls() {
  const {
    status,
    isLoading,
    startDemo,
    pauseDemo,
    resetDemo,
    isStarting,
    isPausing,
    isResetting
  } = useDemo();

  const [ratePerMinute, setRatePerMinute] = useState(60);

  const handleStart = () => {
    startDemo({ rate_per_minute: ratePerMinute });
  };

  const handlePause = () => {
    pauseDemo();
  };

  const handleReset = () => {
    if (confirm('This will delete recent classifications and reset the demo. Continue?')) {
      resetDemo();
    }
  };

  const formatElapsedTime = (seconds: number | null) => {
    if (!seconds) return '0s';

    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);

    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const isRunning = status?.is_running ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🎬 Demo Controls
          {isRunning && (
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-500/10 text-green-600 text-sm font-medium">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Running
            </span>
          )}
        </CardTitle>
        <CardDescription>
          Control the continuous alert generation demo
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Control Buttons */}
        <div className="flex items-center gap-3">
          {!isRunning ? (
            <Button
              onClick={handleStart}
              disabled={isStarting}
              className="gap-2"
              size="lg"
            >
              {isStarting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Start Demo
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handlePause}
              disabled={isPausing}
              variant="secondary"
              className="gap-2"
              size="lg"
            >
              {isPausing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Pausing...
                </>
              ) : (
                <>
                  <Pause className="w-4 h-4" />
                  Pause Demo
                </>
              )}
            </Button>
          )}

          <Button
            onClick={handleReset}
            disabled={isResetting}
            variant="outline"
            className="gap-2"
            size="lg"
          >
            {isResetting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Resetting...
              </>
            ) : (
              <>
                <RotateCcw className="w-4 h-4" />
                Reset
              </>
            )}
          </Button>
        </div>

        {/* Rate Slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-foreground">
              Alert Generation Rate
            </label>
            <span className="text-sm text-muted-foreground font-mono">
              {ratePerMinute} alerts/min
            </span>
          </div>
          <input
            type="range"
            min="10"
            max="1200"
            step="10"
            value={ratePerMinute}
            onChange={(e) => setRatePerMinute(Number(e.target.value))}
            disabled={isRunning}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: isRunning
                ? undefined
                : `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) ${((ratePerMinute - 10) / 1190) * 100}%, hsl(var(--muted)) ${((ratePerMinute - 10) / 1190) * 100}%, hsl(var(--muted)) 100%)`
            }}
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>10/min</span>
            <span>600/min</span>
            <span>1200/min</span>
          </div>
        </div>

        {/* Live Statistics */}
        {status && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Elapsed Time</p>
              <p className="text-lg font-semibold text-foreground font-mono">
                {formatElapsedTime(status.elapsed_seconds)}
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Alerts Sent</p>
              <p className="text-lg font-semibold text-foreground font-mono">
                {status.alerts_sent.toLocaleString()}
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Alerts Processed</p>
              <p className="text-lg font-semibold text-foreground font-mono">
                {status.estimated_alerts_processed.toLocaleString()}
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Current Rate</p>
              <p className="text-lg font-semibold text-foreground font-mono">
                {status.rate_per_minute}/min
              </p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && !status && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
