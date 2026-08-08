import React, { useState, useEffect } from 'react';
import { 
  mockResources, 
  mockTickerAlerts, 
  mockScheduleEntries, 
  mockInitialChatHistory, 
  mockUserProfile 
} from './data/mockData';
import { ResourceItem, DayScheduleEntry, TickerAlert, ChatMessage } from './types';
import { Header } from './components/Header';
import { RightSideRibbon } from './components/RightSideRibbon';
import { PredictionTicker } from './components/PredictionTicker';
import { ResourceMap } from './components/ResourceMap';
import { ResourceDetailModal } from './components/ResourceDetailModal';
import { YourDayCard } from './components/YourDayCard';
import { RagChatAssistant } from './components/RagChatAssistant';
import { ResourceAnalyticsChart } from './components/ResourceAnalyticsChart';
import { WifiApTelemetry } from './components/WifiApTelemetry';
import { ApiIntegrationModal } from './components/ApiIntegrationModal';

export default function App() {
  const [activeView, setActiveView] = useState<'dashboard' | 'telemetry' | 'analytics'>('dashboard');
  const [resources, setResources] = useState<ResourceItem[]>(mockResources);
  const [tickerAlerts, setTickerAlerts] = useState<TickerAlert[]>(mockTickerAlerts);
  const [scheduleEntries, setScheduleEntries] = useState<DayScheduleEntry[]>(mockScheduleEntries);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(mockInitialChatHistory);
  const [selectedResource, setSelectedResource] = useState<ResourceItem | null>(null);
  
  const [isSimulating, setIsSimulating] = useState<boolean>(true);
  const [useLiveBackend, setUseLiveBackend] = useState<boolean>(false);
  const [apiModalOpen, setApiModalOpen] = useState<boolean>(false);
  const [copilotDrawerOpen, setCopilotDrawerOpen] = useState<boolean>(false);
  const [loadBalanceScore, setLoadBalanceScore] = useState<number>(92);

  // Simulation Clock
  const [liveClock, setLiveClock] = useState<string>('14:24 PST');

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setLiveClock(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' PST');
      
      // If simulation is active, subtly fluctuate occupancy values
      if (isSimulating) {
        setResources((prev) =>
          prev.map((res) => {
            const delta = Math.floor(Math.random() * 5) - 2; // -2 to +2
            const newOcc = Math.min(Math.max(res.currentOccupancy + delta, 15), 99);
            
            // Recalculate state bucket
            let newBucket = res.stateBucket;
            if (newOcc < 50) newBucket = 'empty';
            else if (newOcc <= 80) newBucket = 'moderate';
            else if (newOcc <= 95) newBucket = 'full';
            else newBucket = 'overflow';

            return {
              ...res,
              currentOccupancy: newOcc,
              capacityCurrent: Math.round((newOcc / 100) * res.capacityMax),
              stateBucket: newBucket,
            };
          })
        );
      }
    }, 4000);

    return () => clearInterval(timer);
  }, [isSimulating]);

  // Attempt fetch if live backend toggle is turned on
  useEffect(() => {
    if (useLiveBackend) {
      // Endpoint 1: http://localhost:8000/forecast
      // Endpoint 2: http://localhost:8000/report/daily/u_042
      Promise.all([
        fetch('http://localhost:8000/forecast').then((res) => res.json()),
        fetch('http://localhost:8000/report/daily/u_042').then((res) => res.json()),
      ])
        .then(([forecastData, userData]) => {
          if (forecastData && Array.isArray(forecastData)) {
            setResources(forecastData);
          }
          if (userData && userData.schedule) {
            setScheduleEntries(userData.schedule);
            if (userData.load_balance_score) {
              setLoadBalanceScore(userData.load_balance_score);
            }
          }
        })
        .catch((err) => {
          console.log('Local FastAPI server offline, remaining on React mock state.', err);
        });
    }
  }, [useLiveBackend]);

  // Handler: Accept Load-Balanced Recommendation
  const handleAcceptRecommendation = (id: string) => {
    setScheduleEntries((prev) =>
      prev.map((entry) =>
        entry.id === id ? { ...entry, status: 'accepted' as const } : entry
      )
    );
    setLoadBalanceScore((prev) => Math.min(prev + 3, 99));

    // Add ticker notification
    const acceptedEntry = scheduleEntries.find((e) => e.id === id);
    if (acceptedEntry) {
      setTickerAlerts((prev) => [
        {
          id: `t_${Date.now()}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          resourceName: 'Student u_042',
          type: 'optimization',
          message: `Accepted recommendation for ${acceptedEntry.category}: ${acceptedEntry.recommendation.activity} at ${acceptedEntry.recommendation.time}.`,
        },
        ...prev,
      ]);
    }
  };

  // Handler: Modify Schedule
  const handleModifySchedule = (id: string, newTime: string, newLocation: string) => {
    setScheduleEntries((prev) =>
      prev.map((entry) => {
        if (entry.id === id) {
          return {
            ...entry,
            status: 'modified' as const,
            recommendation: {
              ...entry.recommendation,
              time: newTime,
              location: newLocation,
              statusText: `Custom: ${newTime} (${newLocation})`,
            },
          };
        }
        return entry;
      })
    );
  };

  // Handler: Trigger 18:00 Peak Hour Rush Simulation
  const handleTriggerPeakHour = () => {
    setResources((prev) =>
      prev.map((res) => {
        if (res.id === 'res_library' || res.id === 'res_gym') {
          return {
            ...res,
            currentOccupancy: 98,
            capacityCurrent: Math.round(0.98 * res.capacityMax),
            stateBucket: 'overflow' as const,
            trend: 'up' as const,
            trendValue: '+32% peak rush',
          };
        }
        return res;
      })
    );

    setTickerAlerts((prev) => [
      {
        id: `t_peak_${Date.now()}`,
        timestamp: '18:00',
        resourceName: 'Campus Twin Grid',
        type: 'critical',
        message: 'SIMULATION: 18:00 Peak Rush triggered! Library & Gym capacity hit 98% Overflow state.',
      },
      ...prev,
    ]);
  };

  // Handler: Ask RAG Assistant Query
  const handleSendChatMessage = (query: string) => {
    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatHistory((prev) => [...prev, userMsg]);

    // Generate context-aware watsonx assistant answer based on resources state
    setTimeout(() => {
      let botResponse = '';
      let sources = [
        'IBM watsonx RAG Knowledge Base • Vector Collection #402',
        'Campus AP Telemetry Feed (148 AP Nodes)',
      ];
      let suggestedActions = [
        'View 24-hr Library Occupancy Forecast',
        'Check Science Hub Quiet Study Pods',
      ];

      const queryLower = query.toLowerCase();

      if (queryLower.includes('library') || queryLower.includes('study')) {
        const lib = resources.find((r) => r.id === 'res_library');
        const sci = resources.find((r) => r.id === 'res_science_hub');
        botResponse = `Currently, the Main Library is at ${lib?.currentOccupancy || 88}% capacity (${lib?.capacityCurrent} occupants). I recommend shifting your study block to ${sci?.name}, which is currently only at ${sci?.currentOccupancy || 38}% capacity with average WiFi throughput of ${sci?.averageSpeedMbps} Mbps.`;
        sources.push(`Main Library WiFi AP Count: ${lib?.wifiApNodesCount}`);
      } else if (queryLower.includes('gym') || queryLower.includes('workout')) {
        const gym = resources.find((r) => r.id === 'res_gym');
        botResponse = `The Campus Gym is currently at ${gym?.currentOccupancy || 96}% capacity (Overflow). Peak queue time for power racks is ~25 minutes. Shifting your workout block 30 minutes earlier or visiting West Quad Gym will save you ~25 minutes of wait time.`;
        sources.push('Gym IoT Sensor Gate Count');
      } else if (queryLower.includes('cafeteria') || queryLower.includes('eat') || queryLower.includes('lunch')) {
        const caf = resources.find((r) => r.id === 'res_cafeteria');
        botResponse = `North Cafeteria is in an optimal low-density window (${caf?.currentOccupancy}% capacity). Queue delay at the main line is under 3 minutes.`;
      } else {
        botResponse = `Based on current Digital Twin telemetry across all 5 campus hotspots, overall campus congestion is at 68%. The best load-balanced quiet zones right now are Science Hub Study Pods (38% full) and North Cafeteria Terrace (42% full).`;
      }

      const botMsg: ChatMessage = {
        id: `bot_${Date.now()}`,
        sender: 'bot',
        text: botResponse,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources,
        suggestedActions,
      };

      setChatHistory((prev) => [...prev, botMsg]);
    }, 600);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans selection:bg-cyan-500 selection:text-white flex flex-col">
      
      {/* Header */}
      <Header
        user={mockUserProfile}
        liveClock={liveClock}
        isSimulating={isSimulating}
        setIsSimulating={setIsSimulating}
        onOpenApiModal={() => setApiModalOpen(true)}
        onOpenCopilotDrawer={() => setCopilotDrawerOpen(true)}
        loadBalanceScore={loadBalanceScore}
      />

      {/* Main Layout Container with Right Edge Side Ribbon */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto relative pr-0 sm:pr-12">
        
        {/* Main Workspace Content Area */}
        <main className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-5">
          
          {/* Top Row - Ticker */}
          <PredictionTicker alerts={tickerAlerts} />

          {/* Views */}
          {activeView === 'dashboard' && (
            <>
              {/* Top Row: Grid of Resource Cards */}
              <ResourceMap
                resources={resources}
                onSelectResource={(res) => setSelectedResource(res)}
              />

              {/* Middle Section: "Your Day" Card */}
              <YourDayCard
                entries={scheduleEntries}
                onAcceptRecommendation={handleAcceptRecommendation}
                onModifySchedule={handleModifySchedule}
                loadBalanceScore={loadBalanceScore}
              />

              {/* Bottom Section: Recharts Analytics */}
              <ResourceAnalyticsChart resources={resources} />
            </>
          )}

          {activeView === 'analytics' && (
            <ResourceAnalyticsChart resources={resources} />
          )}

          {activeView === 'telemetry' && (
            <WifiApTelemetry />
          )}

        </main>

        {/* Minimalist Vertical Side Ribbon on Right Edge */}
        <RightSideRibbon
          onOpenCopilotDrawer={() => setCopilotDrawerOpen(true)}
          onOpenApiModal={() => setApiModalOpen(true)}
          isSimulating={isSimulating}
          onToggleSimulation={() => setIsSimulating(!isSimulating)}
          activeView={activeView}
          setActiveView={setActiveView}
          unreadCopilotMessagesCount={1}
        />

      </div>

      {/* Slide-out RAG Chat Assistant Drawer */}
      <RagChatAssistant
        isOpen={copilotDrawerOpen}
        onClose={() => setCopilotDrawerOpen(false)}
        messages={chatHistory}
        onSendMessage={handleSendChatMessage}
        resources={resources}
      />

      {/* Resource Detail Modal */}
      <ResourceDetailModal
        resource={selectedResource}
        onClose={() => setSelectedResource(null)}
        onAskRagAssistant={(q) => {
          setCopilotDrawerOpen(true);
          handleSendChatMessage(q);
        }}
      />

      {/* API Integration Modal */}
      <ApiIntegrationModal
        isOpen={apiModalOpen}
        onClose={() => setApiModalOpen(false)}
        useLiveBackend={useLiveBackend}
        setUseLiveBackend={setUseLiveBackend}
      />

    </div>
  );
}
