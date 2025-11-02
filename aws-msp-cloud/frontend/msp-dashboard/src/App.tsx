import { useCallback, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LiveDemoTab } from '@/components/tabs/LiveDemoTab';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import { SystemStatusTab } from '@/components/tabs/SystemStatusTab';
import { TicketsTab } from '@/components/tabs/TicketsTab';
import type { WebSocketMessage } from '@/types/api';

function App() {
  // WebSocket message handler
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    console.log('App: WebSocket message received', message);

    // Handle different message types
    switch (message.type) {
      case 'connection_established':
        console.log('App: WebSocket connection established', message.message);
        break;
      case 'alert_update':
        console.log('App: Alert update received', message.data);
        // The useAlerts hook will automatically refetch when alerts are updated
        break;
      case 'pong':
        // Ping/pong for connection health - no action needed
        break;
      default:
        console.log('App: Unknown message type', message);
    }
  }, []);

  // Initialize WebSocket connection
  const { isConnected } = useWebSocket(handleWebSocketMessage);

  // Tab state
  const [activeTab, setActiveTab] = useState('demo');

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-primary-foreground font-bold text-lg">M</span>
                </div>
                <h1 className="text-2xl font-bold text-foreground">MSP Alert Dashboard</h1>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-muted-foreground">
                  WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="demo">🎬 Live Demo</TabsTrigger>
            <TabsTrigger value="analytics">📊 Analytics</TabsTrigger>
            <TabsTrigger value="tickets">🎫 Tickets</TabsTrigger>
            <TabsTrigger value="status">⚙️ System Status</TabsTrigger>
          </TabsList>

          <TabsContent value="demo">
            <LiveDemoTab />
          </TabsContent>

          <TabsContent value="analytics">
            <AnalyticsTab />
          </TabsContent>

          <TabsContent value="tickets">
            <TicketsTab />
          </TabsContent>

          <TabsContent value="status">
            <SystemStatusTab />
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card mt-12">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <p>
              MSP Alert Triage System - Real-time alert monitoring and automated suppression
            </p>
            <p>Target: 90%+ suppression rate</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
