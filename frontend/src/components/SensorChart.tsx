import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { HistoricalPoint } from '../types';

interface Props {
  data: HistoricalPoint[];
  tag: string;
  unit?: string;
}

function formatTime(timeStr: string): string {
  const d = new Date(timeStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function SensorChart({ data, tag, unit }: Props) {
  return (
    <div>
      <h3 style={{ margin: '0 0 16px', fontSize: '16px', color: '#1a1a2e' }}>
        {tag.replace(/\//g, ' › ').replace(/_/g, ' ')}
        {unit ? ` (${unit})` : ''}
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="time"
            tickFormatter={formatTime}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            label={unit ? { value: unit, angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#94a3b8' } } : undefined}
          />
          <Tooltip
            formatter={(value: number) => [value.toFixed(2), unit || 'Value']}
            labelFormatter={(label: string) => new Date(label).toLocaleString()}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
