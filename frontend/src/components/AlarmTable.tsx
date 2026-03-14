import React from 'react';
import type { Alarm } from '../types';

interface Props {
  alarms: Alarm[];
  onAcknowledge?: (id: string) => void;
  canAcknowledge: boolean;
}

const severityColors: Record<string, { bg: string; text: string }> = {
  critical: { bg: '#fee2e2', text: '#dc2626' },
  warning: { bg: '#fff7ed', text: '#ea580c' },
  info: { bg: '#eff6ff', text: '#2563eb' },
};

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString();
}

export default function AlarmTable({ alarms, onAcknowledge, canAcknowledge }: Props) {
  if (alarms.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px', color: '#94a3b8', background: '#f8fafc', borderRadius: '12px', border: '1px dashed #e2e8f0' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>✅</div>
        <p style={{ fontSize: '18px', margin: 0 }}>No alarms</p>
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <thead>
          <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
            {['Tag', 'Message', 'Severity', 'Time', 'Status', 'Actions'].map((h) => (
              <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {alarms.map((alarm, i) => {
            const colors = severityColors[alarm.severity] || severityColors.info;
            return (
              <tr
                key={alarm.id}
                style={{
                  borderBottom: i < alarms.length - 1 ? '1px solid #f1f5f9' : 'none',
                  opacity: alarm.acknowledged ? 0.6 : 1,
                  background: alarm.acknowledged ? '#fafafa' : 'white',
                }}
              >
                <td style={{ padding: '12px 16px', fontSize: '13px', fontFamily: 'monospace', color: '#1a1a2e', textDecoration: alarm.acknowledged ? 'line-through' : 'none' }}>
                  {alarm.tag}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '13px', color: '#475569' }}>
                  {alarm.message}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    background: colors.bg,
                    color: colors.text,
                    borderRadius: '4px',
                    padding: '2px 8px',
                    fontSize: '11px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                  }}>
                    {alarm.severity}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '12px', color: '#64748b' }}>
                  {formatTime(alarm.timestamp)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {alarm.acknowledged ? (
                    <span style={{ fontSize: '12px', color: '#16a34a' }}>
                      ✓ Ack'd by {alarm.acknowledged_by || 'unknown'}
                    </span>
                  ) : (
                    <span style={{ fontSize: '12px', color: '#ea580c', fontWeight: 600 }}>Active</span>
                  )}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  {canAcknowledge && !alarm.acknowledged && onAcknowledge && (
                    <button
                      onClick={() => onAcknowledge(alarm.id)}
                      style={{
                        padding: '5px 12px',
                        background: '#0f3460',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}
                    >
                      Acknowledge
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
