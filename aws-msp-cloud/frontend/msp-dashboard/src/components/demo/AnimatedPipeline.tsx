import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useDemo } from '@/hooks/useDemo';

interface Alert {
  id: string;
  stage: 'kafka' | 'tier1' | 'tier2' | 'tier3' | 'orchestrator' | 'done';
  classification?: 'NOISE' | 'ACTIONABLE' | 'CRITICAL' | 'DUPLICATE';
  timestamp: number;
}

const STAGE_DURATION = 800; // ms per stage
const SPAWN_INTERVAL = 2000; // spawn new alert every 2s

export function AnimatedPipeline() {
  const { status } = useDemo();
  const [alerts, setAlerts] = useState<Alert[]>([]);

  // Spawn new alerts when demo is running
  useEffect(() => {
    if (!status?.is_running) return;

    const spawnAlert = () => {
      const newAlert: Alert = {
        id: `alert-${Date.now()}-${Math.random()}`,
        stage: 'kafka',
        timestamp: Date.now(),
      };
      setAlerts(prev => [...prev, newAlert]);
    };

    // Spawn initial alert immediately
    spawnAlert();

    // Then spawn at intervals
    const interval = setInterval(spawnAlert, SPAWN_INTERVAL);
    return () => clearInterval(interval);
  }, [status?.is_running]);

  // Progress alerts through stages
  useEffect(() => {
    const progressInterval = setInterval(() => {
      setAlerts(prev => {
        const now = Date.now();
        return prev
          .map(alert => {
            const elapsedSinceStage = now - alert.timestamp;

            if (elapsedSinceStage >= STAGE_DURATION) {
              // Move to next stage
              const stageOrder: Alert['stage'][] = ['kafka', 'tier1', 'tier2', 'tier3', 'orchestrator', 'done'];
              const currentIndex = stageOrder.indexOf(alert.stage);

              if (currentIndex < stageOrder.length - 1) {
                const nextStage = stageOrder[currentIndex + 1];

                // Assign classification at tier2
                let classification = alert.classification;
                if (nextStage === 'tier2' && !classification) {
                  const rand = Math.random();
                  if (rand < 0.1) classification = 'DUPLICATE';
                  else if (rand < 0.7) classification = 'NOISE';
                  else if (rand < 0.9) classification = 'ACTIONABLE';
                  else classification = 'CRITICAL';
                }

                return {
                  ...alert,
                  stage: nextStage,
                  classification,
                  timestamp: now,
                };
              }
            }

            return alert;
          })
          .filter(alert => alert.stage !== 'done'); // Remove completed alerts
      });
    }, 100);

    return () => clearInterval(progressInterval);
  }, []);

  const getStagePosition = (stage: Alert['stage']): { x: number; y: number } => {
    const positions = {
      kafka: { x: 5, y: 50 },
      tier1: { x: 25, y: 20 },
      tier2: { x: 45, y: 50 },
      tier3: { x: 65, y: 80 },
      orchestrator: { x: 85, y: 50 },
      done: { x: 100, y: 50 },
    };
    return positions[stage];
  };

  const getAlertColor = (classification?: Alert['classification']): string => {
    if (!classification) return 'bg-blue-500';
    switch (classification) {
      case 'DUPLICATE': return 'bg-gray-400';
      case 'NOISE': return 'bg-blue-400';
      case 'ACTIONABLE': return 'bg-green-500';
      case 'CRITICAL': return 'bg-red-500';
      default: return 'bg-blue-500';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Alert Flow</CardTitle>
        <CardDescription>
          Watch alerts flow through the ML pipeline in real-time
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Pipeline Stages */}
        <div className="relative h-64 bg-slate-900 rounded-lg overflow-hidden">
          {/* Stage Nodes */}
          <div className="absolute top-1/2 left-[5%] -translate-y-1/2 bg-slate-800 border-2 border-blue-500 rounded-lg px-4 py-2 text-xs font-medium text-white">
            Kafka
          </div>
          <div className="absolute top-[20%] left-[25%] -translate-y-1/2 bg-slate-800 border-2 border-blue-400 rounded-lg px-3 py-2 text-xs font-medium text-white">
            <div>Tier 1</div>
            <div className="text-gray-400 text-[10px]">Duplicate</div>
          </div>
          <div className="absolute top-1/2 left-[45%] -translate-y-1/2 bg-slate-800 border-2 border-purple-500 rounded-lg px-3 py-2 text-xs font-medium text-white">
            <div>Tier 2</div>
            <div className="text-gray-400 text-[10px]">Classify</div>
          </div>
          <div className="absolute top-[80%] left-[65%] -translate-y-1/2 bg-slate-800 border-2 border-amber-500 rounded-lg px-3 py-2 text-xs font-medium text-white">
            <div>Tier 3</div>
            <div className="text-gray-400 text-[10px]">Score</div>
          </div>
          <div className="absolute top-1/2 left-[85%] -translate-y-1/2 bg-slate-800 border-2 border-pink-500 rounded-lg px-3 py-2 text-xs font-medium text-white">
            <div className="text-[10px]">Action</div>
            <div className="text-[10px]">Orchestrator</div>
          </div>

          {/* Animated Alert Particles */}
          <AnimatePresence>
            {alerts.map(alert => {
              const pos = getStagePosition(alert.stage);
              const color = getAlertColor(alert.classification);

              return (
                <motion.div
                  key={alert.id}
                  className={`absolute w-3 h-3 rounded-full ${color} shadow-lg`}
                  initial={{ left: `${getStagePosition('kafka').x}%`, top: `${getStagePosition('kafka').y}%`, opacity: 0, scale: 0 }}
                  animate={{
                    left: `${pos.x}%`,
                    top: `${pos.y}%`,
                    opacity: 1,
                    scale: 1,
                  }}
                  exit={{ opacity: 0, scale: 0 }}
                  transition={{ duration: 0.6, ease: 'easeInOut' }}
                />
              );
            })}
          </AnimatePresence>

          {/* Connection Lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
            <defs>
              <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style={{ stopColor: '#3b82f6', stopOpacity: 0.3 }} />
                <stop offset="100%" style={{ stopColor: '#60a5fa', stopOpacity: 0.3 }} />
              </linearGradient>
            </defs>
            {/* Kafka to Tier1 */}
            <line x1="15%" y1="50%" x2="25%" y2="20%" stroke="url(#grad1)" strokeWidth="2" strokeDasharray="4 4" />
            {/* Tier1 to Tier2 */}
            <line x1="30%" y1="20%" x2="45%" y2="50%" stroke="url(#grad1)" strokeWidth="2" strokeDasharray="4 4" />
            {/* Tier2 to Tier3 */}
            <line x1="50%" y1="50%" x2="65%" y2="80%" stroke="url(#grad1)" strokeWidth="2" strokeDasharray="4 4" />
            {/* Tier3 to Orchestrator */}
            <line x1="70%" y1="80%" x2="85%" y2="50%" stroke="url(#grad1)" strokeWidth="2" strokeDasharray="4 4" />
          </svg>
        </div>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-gray-400"></div>
            <span className="text-muted-foreground">Duplicate</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-400"></div>
            <span className="text-muted-foreground">Noise</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-muted-foreground">Actionable</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span className="text-muted-foreground">Critical</span>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-4 p-3 bg-muted/50 rounded-lg">
          <div className="text-sm text-muted-foreground">
            Active alerts in pipeline: <span className="font-mono font-bold text-foreground">{alerts.length}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
