import React, { useEffect, useRef, useState, useCallback } from 'react';
import { getSensors } from '../api';
import type { SensorReading, Alarm } from '../types';
import SensorCard from '../components/SensorCard';
import { getAlarms } from '../api';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`;

export default function DashboardPage() {
  const [sensors, setSensors] = useState<Record<string, SensorReading>>({});
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [error, setError] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [sensorsData, alarmsData] = await Promise.all([getSensors(), getAlarms()]);
      setSensors(sensorsData);
      setAlarms(alarmsData);
      setError('');
    } catch {
      setError('Failed to load dashboard data. Is the backend running?');
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const reading: SensorReading = JSON.parse(event.data);
        if (reading.tag) {
          setSensors((prev) => ({ ...prev, [reading.tag]: reading }));
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      // Auto-reconnect after 3 seconds
      reconnectRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    fetchData();
    connectWebSocket();
    // Refresh alarms every 15s
    const interval = setInterval(() => {
      getAlarms().then(setAlarms).catch(() => {});
    }, 15000);

    return () => {
      clearInterval(interval);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchData, connectWebSocket]);

  const activeAlarms = alarms.filter((a) => !a.acknowledged);
  const sortedTags = Object.keys(sensors).sort();

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', color: '#1a1a2e' }}>Live Dashboard</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '14px' }}>
            {sortedTags.length} sensors monitored
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* WS Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: wsConnected ? '#22c55e' : '#ef4444',
            }} />
            <span style={{ fontSize: '13px', color: '#64748b' }}>
              {wsConnected ? 'Live' : 'Connecting...'}
            </span>
          </div>
          {/* Active alarms badge */}
          {activeAlarms.length > 0 && (
            <div style={{
              background: '#fee2e2',
              border: '1px solid #fca5a5',
              borderRadius: '20px',
              padding: '4px 12px',
              fontSize: '13px',
              color: '#dc2626',
              fontWeight: 600,
            }}>
              ⚠️ {activeAlarms.length} Active Alarm{activeAlarms.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>

      {error && (
        <div style={{
          background: '#fee2e2',
          border: '1px solid #fca5a5',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '24px',
          color: '#dc2626',
        }}>
          {error}
        </div>
      )}

      {/* Sensor Grid */}
      {sortedTags.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '80px 20px',
          color: '#94a3b8',
          background: '#f8fafc',
          borderRadius: '12px',
          border: '1px dashed #e2e8f0',
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📡</div>
          <p style={{ fontSize: '18px', margin: 0 }}>Waiting for sensor data...</p>
          <p style={{ fontSize: '14px', marginTop: '8px' }}>Make sure the simulator is running</p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: '16px',
        }}>
          {sortedTags.map((tag) => (
            <SensorCard key={tag} tag={tag} reading={sensors[tag]} />
          ))}
        </div>
      )}
    </div>
  );
}
