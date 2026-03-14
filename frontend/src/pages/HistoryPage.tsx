import React, { useState } from 'react';
import { getHistory } from '../api';
import type { HistoricalPoint } from '../types';
import SensorChart from '../components/SensorChart';

const KNOWN_TAGS = [
  'pump1/flow', 'pump1/pressure', 'pump1/temperature', 'pump1/current', 'pump1/vibration',
  'pump2/flow', 'pump2/pressure', 'pump2/temperature', 'pump2/current', 'pump2/vibration',
  'tank1/level', 'tank2/level',
  'compressor/pressure', 'compressor/temperature',
  'heat_exchanger/inlet_temp', 'heat_exchanger/outlet_temp',
  'conveyor/speed', 'conveyor/current',
  'boiler/pressure', 'boiler/temperature', 'boiler/flow',
];

export default function HistoryPage() {
  const [selectedTag, setSelectedTag] = useState('');
  const [hours, setHours] = useState(1);
  const [data, setData] = useState<HistoricalPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchHistory = async (tag: string, h: number) => {
    if (!tag) return;
    setLoading(true);
    setError('');
    try {
      const result = await getHistory(tag, h);
      setData(result);
    } catch {
      setError('Failed to fetch historical data');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleTagChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const tag = e.target.value;
    setSelectedTag(tag);
    if (tag) fetchHistory(tag, hours);
  };

  const handleHoursChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const h = Number(e.target.value);
    setHours(h);
    if (selectedTag) fetchHistory(selectedTag, h);
  };

  const selectStyle = {
    padding: '10px 12px',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '14px',
    color: '#1a1a2e',
    background: 'white',
    cursor: 'pointer',
    minWidth: '200px',
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ margin: '0 0 8px', fontSize: '24px', color: '#1a1a2e' }}>Historical Data</h1>
      <p style={{ margin: '0 0 24px', color: '#64748b', fontSize: '14px' }}>View time-series data from InfluxDB</p>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600, color: '#475569' }}>
            Select Tag
          </label>
          <select value={selectedTag} onChange={handleTagChange} style={selectStyle}>
            <option value="">-- Choose a sensor --</option>
            {KNOWN_TAGS.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600, color: '#475569' }}>
            Time Range
          </label>
          <select value={hours} onChange={handleHoursChange} style={selectStyle}>
            <option value={1}>Last 1 hour</option>
            <option value={6}>Last 6 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={72}>Last 3 days</option>
          </select>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: '8px', padding: '12px 16px', marginBottom: '16px', color: '#dc2626' }}>
          {error}
        </div>
      )}

      {!selectedTag ? (
        <div style={{ textAlign: 'center', padding: '80px 20px', color: '#94a3b8', background: '#f8fafc', borderRadius: '12px', border: '1px dashed #e2e8f0' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📈</div>
          <p style={{ fontSize: '18px', margin: 0 }}>Select a tag to view history</p>
        </div>
      ) : loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#94a3b8' }}>
          <p>Loading data...</p>
        </div>
      ) : data.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#94a3b8', background: '#f8fafc', borderRadius: '12px', border: '1px dashed #e2e8f0' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
          <p style={{ fontSize: '18px', margin: 0 }}>No historical data available</p>
          <p style={{ fontSize: '14px', marginTop: '8px' }}>Data is stored in InfluxDB when the system is running</p>
        </div>
      ) : (
        <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <SensorChart data={data} tag={selectedTag} />
        </div>
      )}
    </div>
  );
}
