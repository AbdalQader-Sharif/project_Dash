import React, { useEffect, useState } from 'react';
import { getAlarms, acknowledgeAlarm } from '../api';
import type { Alarm } from '../types';
import AlarmTable from '../components/AlarmTable';
import { useAuth } from '../contexts/AuthContext';

type Filter = 'all' | 'active' | 'acknowledged';

export default function AlarmsPage() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user, token } = useAuth();

  const fetchAlarms = async () => {
    try {
      const data = await getAlarms();
      setAlarms(data);
      setError('');
    } catch {
      setError('Failed to fetch alarms');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlarms();
    const interval = setInterval(fetchAlarms, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAcknowledge = async (id: string) => {
    if (!token) return;
    try {
      await acknowledgeAlarm(id, token);
      await fetchAlarms();
    } catch {
      setError('Failed to acknowledge alarm');
    }
  };

  const filtered = alarms.filter((a) => {
    if (filter === 'active') return !a.acknowledged;
    if (filter === 'acknowledged') return a.acknowledged;
    return true;
  });

  const canAcknowledge = user?.role === 'admin' || user?.role === 'developer';

  const btnStyle = (active: boolean) => ({
    padding: '8px 16px',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    background: active ? '#0f3460' : 'white',
    color: active ? 'white' : '#475569',
    cursor: 'pointer',
    fontWeight: active ? 600 : 400,
    fontSize: '14px',
  });

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', color: '#1a1a2e' }}>Alarms</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '14px' }}>
            {alarms.filter(a => !a.acknowledged).length} active · {alarms.length} total
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button style={btnStyle(filter === 'all')} onClick={() => setFilter('all')}>All</button>
          <button style={btnStyle(filter === 'active')} onClick={() => setFilter('active')}>Active</button>
          <button style={btnStyle(filter === 'acknowledged')} onClick={() => setFilter('acknowledged')}>Acknowledged</button>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: '8px', padding: '12px 16px', marginBottom: '16px', color: '#dc2626' }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ textAlign: 'center', color: '#94a3b8' }}>Loading alarms...</p>
      ) : (
        <AlarmTable alarms={filtered} onAcknowledge={handleAcknowledge} canAcknowledge={canAcknowledge} />
      )}
    </div>
  );
}
