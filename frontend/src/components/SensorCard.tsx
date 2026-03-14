import React from 'react';
import type { SensorReading } from '../types';

interface Props {
  tag: string;
  reading: SensorReading;
}

function formatTag(tag: string): string {
  return tag.replace(/\//g, ' › ').replace(/_/g, ' ');
}

function timeAgo(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp);
  if (seconds < 5) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
}

export default function SensorCard({ tag, reading }: Props) {
  const isAnomaly = reading.anomaly;

  return (
    <div style={{
      background: isAnomaly ? '#fff5f5' : '#f0fdf4',
      border: `1px solid ${isAnomaly ? '#fca5a5' : '#bbf7d0'}`,
      borderRadius: '10px',
      padding: '16px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      transition: 'border-color 0.3s',
    }}>
      {/* Tag name */}
      <div style={{
        fontSize: '12px',
        color: '#64748b',
        marginBottom: '8px',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        fontWeight: 600,
      }}>
        {formatTag(tag)}
      </div>

      {/* Value */}
      <div style={{
        fontSize: '32px',
        fontWeight: 700,
        color: isAnomaly ? '#dc2626' : '#15803d',
        lineHeight: 1,
        marginBottom: '4px',
      }}>
        {typeof reading.value === 'number' ? reading.value.toFixed(1) : reading.value}
        <span style={{ fontSize: '16px', fontWeight: 400, marginLeft: '4px', color: '#64748b' }}>
          {reading.unit}
        </span>
      </div>

      {/* Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          color: isAnomaly ? '#dc2626' : '#16a34a',
          background: isAnomaly ? '#fee2e2' : '#dcfce7',
          padding: '2px 8px',
          borderRadius: '10px',
        }}>
          {isAnomaly ? '⚠ ANOMALY' : '✓ NORMAL'}
        </span>
        <span style={{ fontSize: '11px', color: '#94a3b8' }}>
          {timeAgo(reading.timestamp)}
        </span>
      </div>
    </div>
  );
}
