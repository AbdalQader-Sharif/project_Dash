export interface SensorReading {
  tag: string;
  value: number;
  unit: string;
  timestamp: number;
  anomaly: boolean;
}

export interface Alarm {
  id: string;
  tag: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
  timestamp: number;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: number;
}

export type UserRole = 'developer' | 'admin' | 'user';

export interface User {
  username: string;
  role: UserRole;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  role: UserRole;
  username: string;
}

export interface HistoricalPoint {
  time: string;
  value: number;
}
