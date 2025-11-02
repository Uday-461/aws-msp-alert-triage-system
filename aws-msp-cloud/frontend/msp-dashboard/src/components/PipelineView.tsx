import { useEffect, useState, useMemo } from 'react';
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  ConnectionLineType,
  type Node,
  type Edge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface PipelineStats {
  tier1_latency: number;
  tier2_latency: number;
  tier3_latency: number;
  alerts_processed: number;
  suppression_rate: number;
}

const initialNodes: Node[] = [
  {
    id: 'kafka',
    type: 'input',
    data: { label: 'Kafka\nsuperops.alerts.raw' },
    position: { x: 50, y: 200 },
    style: {
      background: '#1e293b',
      color: '#e2e8f0',
      border: '2px solid #3b82f6',
      borderRadius: '10px',
      padding: '15px',
      fontSize: '13px',
      fontWeight: 600,
      width: 180,
    },
  },
  {
    id: 'tier1',
    data: {
      label: (
        <div className="text-center">
          <div className="font-bold text-blue-400">Tier 1: Sentence-BERT</div>
          <div className="text-xs text-gray-400 mt-1">Duplicate Detection</div>
          <div className="text-sm text-green-400 mt-2">~10ms</div>
        </div>
      ),
    },
    position: { x: 300, y: 80 },
    style: {
      background: '#1e3a5f',
      color: '#e2e8f0',
      border: '2px solid #60a5fa',
      borderRadius: '12px',
      padding: '20px',
      width: 220,
    },
  },
  {
    id: 'tier2',
    data: {
      label: (
        <div className="text-center">
          <div className="font-bold text-purple-400">Tier 2: DistilBERT</div>
          <div className="text-xs text-gray-400 mt-1">Classification</div>
          <div className="text-sm text-green-400 mt-2">~50ms</div>
        </div>
      ),
    },
    position: { x: 300, y: 220 },
    style: {
      background: '#3a2651',
      color: '#e2e8f0',
      border: '2px solid #a78bfa',
      borderRadius: '12px',
      padding: '20px',
      width: 220,
    },
  },
  {
    id: 'tier3',
    data: {
      label: (
        <div className="text-center">
          <div className="font-bold text-amber-400">Tier 3: RLM/T5</div>
          <div className="text-xs text-gray-400 mt-1">Contextual Scoring</div>
          <div className="text-sm text-green-400 mt-2">~200ms</div>
        </div>
      ),
    },
    position: { x: 300, y: 360 },
    style: {
      background: '#4a3419',
      color: '#e2e8f0',
      border: '2px solid #fbbf24',
      borderRadius: '12px',
      padding: '20px',
      width: 220,
    },
  },
  {
    id: 'orchestrator',
    data: { label: 'Action Orchestrator\nDecision Engine' },
    position: { x: 600, y: 200 },
    style: {
      background: '#1e293b',
      color: '#e2e8f0',
      border: '2px solid #ec4899',
      borderRadius: '10px',
      padding: '15px',
      fontSize: '13px',
      fontWeight: 600,
      width: 180,
    },
  },
  {
    id: 'suppress',
    type: 'output',
    data: { label: 'AUTO-SUPPRESS\n(90%+)' },
    position: { x: 850, y: 100 },
    style: {
      background: '#1e293b',
      color: '#10b981',
      border: '2px solid #10b981',
      borderRadius: '10px',
      padding: '15px',
      fontSize: '13px',
      fontWeight: 600,
      width: 160,
    },
  },
  {
    id: 'escalate',
    type: 'output',
    data: { label: 'ESCALATE\n(~10%)' },
    position: { x: 850, y: 300 },
    style: {
      background: '#1e293b',
      color: '#ef4444',
      border: '2px solid #ef4444',
      borderRadius: '10px',
      padding: '15px',
      fontSize: '13px',
      fontWeight: 600,
      width: 160,
    },
  },
];

const initialEdges: Edge[] = [
  {
    id: 'e-kafka-tier1',
    source: 'kafka',
    target: 'tier1',
    type: ConnectionLineType.SmoothStep,
    animated: true,
    style: { stroke: '#3b82f6', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
  },
  {
    id: 'e-tier1-tier2',
    source: 'tier1',
    target: 'tier2',
    type: ConnectionLineType.SmoothStep,
    animated: true,
    style: { stroke: '#8b5cf6', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' },
  },
  {
    id: 'e-tier2-tier3',
    source: 'tier2',
    target: 'tier3',
    type: ConnectionLineType.SmoothStep,
    animated: true,
    style: { stroke: '#fbbf24', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#fbbf24' },
  },
  {
    id: 'e-tier3-orchestrator',
    source: 'tier3',
    target: 'orchestrator',
    type: ConnectionLineType.SmoothStep,
    animated: true,
    style: { stroke: '#ec4899', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#ec4899' },
  },
  {
    id: 'e-orchestrator-suppress',
    source: 'orchestrator',
    target: 'suppress',
    type: ConnectionLineType.SmoothStep,
    animated: true,
    style: { stroke: '#10b981', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
    label: '90%+',
    labelStyle: { fill: '#10b981', fontWeight: 600 },
  },
  {
    id: 'e-orchestrator-escalate',
    source: 'orchestrator',
    target: 'escalate',
    type: ConnectionLineType.SmoothStep,
    animated: true,
    style: { stroke: '#ef4444', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' },
    label: '~10%',
    labelStyle: { fill: '#ef4444', fontWeight: 600 },
  },
];

export function PipelineView() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // CRITICAL: Memoize empty objects to prevent ReactFlow warning
  const nodeTypes = useMemo(() => ({}), []);
  const edgeTypes = useMemo(() => ({}), []);

  const [stats, setStats] = useState<PipelineStats>({
    tier1_latency: 10,
    tier2_latency: 50,
    tier3_latency: 200,
    alerts_processed: 0,
    suppression_rate: 0,
  });

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(prev => ({
        tier1_latency: 8 + Math.random() * 4,
        tier2_latency: 45 + Math.random() * 10,
        tier3_latency: 190 + Math.random() * 20,
        alerts_processed: prev.alerts_processed + Math.floor(Math.random() * 50),
        suppression_rate: 88 + Math.random() * 8,
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  // Update node labels with live stats
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === 'tier1') {
          return {
            ...node,
            data: {
              ...node.data,
              label: (
                <div className="text-center">
                  <div className="font-bold text-blue-400">Tier 1: Sentence-BERT</div>
                  <div className="text-xs text-gray-400 mt-1">Duplicate Detection</div>
                  <div className="text-sm text-green-400 mt-2">
                    {stats.tier1_latency.toFixed(1)}ms
                  </div>
                </div>
              ),
            },
          };
        }
        if (node.id === 'tier2') {
          return {
            ...node,
            data: {
              ...node.data,
              label: (
                <div className="text-center">
                  <div className="font-bold text-purple-400">Tier 2: DistilBERT</div>
                  <div className="text-xs text-gray-400 mt-1">Classification</div>
                  <div className="text-sm text-green-400 mt-2">
                    {stats.tier2_latency.toFixed(1)}ms
                  </div>
                </div>
              ),
            },
          };
        }
        if (node.id === 'tier3') {
          return {
            ...node,
            data: {
              ...node.data,
              label: (
                <div className="text-center">
                  <div className="font-bold text-amber-400">Tier 3: RLM/T5</div>
                  <div className="text-xs text-gray-400 mt-1">Contextual Scoring</div>
                  <div className="text-sm text-green-400 mt-2">
                    {stats.tier3_latency.toFixed(1)}ms
                  </div>
                </div>
              ),
            },
          };
        }
        if (node.id === 'suppress') {
          return {
            ...node,
            data: {
              ...node.data,
              label: `AUTO-SUPPRESS\n(${stats.suppression_rate.toFixed(1)}%)`,
            },
          };
        }
        return node;
      })
    );
  }, [stats, setNodes]);

  const avgLatency = (stats.tier1_latency + stats.tier2_latency + stats.tier3_latency) / 3;

  return (
    <Card>
      <CardHeader>
        <CardTitle>ML Pipeline Visualization</CardTitle>
        <CardDescription>Real-time 3-tier alert processing pipeline</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Stats Summary */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-muted/50 p-3 rounded-lg">
              <div className="text-xs text-muted-foreground">Avg Latency</div>
              <div className="text-lg font-bold text-green-400">{avgLatency.toFixed(1)}ms</div>
            </div>
            <div className="bg-muted/50 p-3 rounded-lg">
              <div className="text-xs text-muted-foreground">Alerts Processed</div>
              <div className="text-lg font-bold text-blue-400">
                {stats.alerts_processed.toLocaleString()}
              </div>
            </div>
            <div className="bg-muted/50 p-3 rounded-lg">
              <div className="text-xs text-muted-foreground">Suppression Rate</div>
              <div className="text-lg font-bold text-green-400">
                {stats.suppression_rate.toFixed(1)}%
              </div>
            </div>
            <div className="bg-muted/50 p-3 rounded-lg">
              <div className="text-xs text-muted-foreground">Target</div>
              <div className="text-lg font-bold text-muted-foreground">e90%</div>
            </div>
          </div>

          {/* React Flow Pipeline - CRITICAL: Both width and height */}
          <div style={{ width: '100%', height: '500px' }} className="bg-background border border-border rounded-lg">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              fitView
              attributionPosition="bottom-left"
            >
              <Background color="#334155" gap={16} />
              <Controls />
            </ReactFlow>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-muted-foreground">Tier 1: Duplicate Detection</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500"></div>
              <span className="text-muted-foreground">Tier 2: Classification</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500"></div>
              <span className="text-muted-foreground">Tier 3: Contextual Scoring</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
