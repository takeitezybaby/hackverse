export type CongestionState = 'empty' | 'moderate' | 'full' | 'overflow' | 'green' | 'yellow' | 'orange' | 'red' | 'purple';

export interface ResourceItem {
  id: string;
  name: string;
  category: 'library' | 'gym' | 'cafeteria' | 'student_center' | 'lab';
  currentOccupancy: number; // Percentage 0 - 100+
  capacityMax: number;
  capacityCurrent: number;
  trend: 'up' | 'down' | 'steady';
  trendValue: string; // e.g. "+12% in last hr"
  stateBucket: CongestionState; // green: <50%, yellow: 50-80%, orange/red: 80-95%, purple/overflow: >95%
  peakHours: string;
  predictedOverflowTime?: string;
  wifiApNodesCount: number;
  averageSpeedMbps: number;
  noiseLevelDb: number;
  floors: {
    name: string;
    occupancy: number;
    availableSeats: number;
  }[];
  hourlyForecast: {
    time: string;
    occupancy: number;
    historicalAvg: number;
  }[];
}

export interface HabitItem {
  id: string;
  time: string;
  activity: string;
  location: string;
  usualOccupancy: number; // e.g. 95
  isCongested: boolean;
  statusText: string; // "Predicted: 95% Full"
}

export interface RecommendationItem {
  id: string;
  time: string;
  activity: string;
  location: string;
  predictedOccupancy: number; // e.g. 60
  timeSavedMinutes: number;
  statusText: string; // "Predicted: 60% Full"
  reasoning: string;
}

export interface DayScheduleEntry {
  id: string;
  habit: HabitItem;
  recommendation: RecommendationItem;
  status: 'pending' | 'accepted' | 'modified';
  category: 'study' | 'workout' | 'dining' | 'social';
}

export interface TickerAlert {
  id: string;
  timestamp: string;
  resourceName: string;
  type: 'warning' | 'info' | 'critical' | 'optimization';
  message: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
  sources?: string[];
  suggestedActions?: string[];
}

export interface UserProfile {
  id: string; // "u_042"
  name: string; // "Alex Mercer"
  role: string; // "Computer Science Senior"
  avatar: string;
  status: string; // "In Class - Engineering Quad"
  loadBalanceScore: number; // 88%
  hoursSavedThisWeek: number; // 3.5
  preferredQuietZones: string[];
}
