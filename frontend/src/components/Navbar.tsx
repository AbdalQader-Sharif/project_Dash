import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getAlarms } from '../api';
import { useState, useEffect } from 'react';

const roleColors: Record<string, string> = {
  developer: '#7c3aed',
  admin: '#2563eb',
  user: '#16a34a',
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const [activeAlarmCount, setActiveAlarmCount] = useState(0);

  useEffect(() => {
    const fetch = () => {
      getAlarms(false).then((alarms) => setActiveAlarmCount(alarms.length)).catch(() => {});
    };
    fetch();
    const interval = setInterval(fetch, 15000);
    return () => clearInterval(interval);
  }, []);

  const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
    textDecoration: 'none',
    color: isActive ? '#0f3460' : '#475569',
    fontWeight: isActive ? 700 : 500,
    padding: '6px 12px',
    borderRadius: '6px',
    background: isActive ? '#e0e7ff' : 'transparent',
    fontSize: '14px',
  });

  return (
    <nav style={{
      background: 'white',
      borderBottom: '1px solid #e2e8f0',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: '60px',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Left: Title */}
      <div style={{ fontWeight: 700, fontSize: '18px', color: '#1a1a2e' }}>
        🏭 PLC Dashboard
      </div>

      {/* Center: Nav links */}
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        <NavLink to="/dashboard" style={navLinkStyle}>Dashboard</NavLink>
        <NavLink to="/alarms" style={navLinkStyle}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            Alarms
            {activeAlarmCount > 0 && (
              <span style={{
                background: '#ef4444',
                color: 'white',
                borderRadius: '10px',
                padding: '1px 6px',
                fontSize: '11px',
                fontWeight: 700,
              }}>
                {activeAlarmCount}
              </span>
            )}
          </span>
        </NavLink>
        <NavLink to="/history" style={navLinkStyle}>History</NavLink>
      </div>

      {/* Right: User info + logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '14px', color: '#475569' }}>{user?.username}</span>
        {user?.role && (
          <span style={{
            background: roleColors[user.role] || '#94a3b8',
            color: 'white',
            borderRadius: '4px',
            padding: '2px 8px',
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
          }}>
            {user.role}
          </span>
        )}
        <button
          onClick={logout}
          style={{
            padding: '6px 14px',
            background: 'transparent',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
            color: '#475569',
          }}
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
