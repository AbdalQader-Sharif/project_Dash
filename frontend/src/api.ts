import axios from 'axios';
import type { AuthToken, SensorReading, Alarm, HistoricalPoint } from './types';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export async function login(username: string, password: string): Promise<AuthToken> {
  const response = await api.post<AuthToken>('/auth/login', { username, password });
  return response.data;
}

export async function getSensors(): Promise<Record<string, SensorReading>> {
  const response = await api.get<Record<string, SensorReading>>('/sensors');
  return response.data;
}

export async function getSensor(tag: string): Promise<SensorReading> {
  const response = await api.get<SensorReading>(`/sensors/${tag}`);
  return response.data;
}

export async function getAlarms(acknowledged?: boolean): Promise<Alarm[]> {
  const params: Record<string, string> = {};
  if (acknowledged !== undefined) {
    params.acknowledged = String(acknowledged);
  }
  const response = await api.get<Alarm[]>('/alarms', { params });
  return response.data;
}

export async function acknowledgeAlarm(id: string, token: string): Promise<void> {
  await api.post(
    `/alarms/${id}/acknowledge`,
    {},
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getHistory(tag: string, hours: number = 1): Promise<HistoricalPoint[]> {
  const response = await api.get<HistoricalPoint[]>(`/history/${tag}`, { params: { hours } });
  return response.data;
}

export async function getHealth(): Promise<{ status: string; sensors: number; alarms: number }> {
  const response = await api.get('/health');
  return response.data;
}

export default api;
