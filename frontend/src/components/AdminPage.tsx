import { useEffect, useState, useCallback } from 'react';
import { admin as adminAPI } from '../api';
import { useAuthStore } from '../store/authStore';
import { useUIStore } from '../store/uiStore';
import type { UserSummary, AuditLogEntry } from '../types';

type Tab = 'users' | 'audit';

export function AdminPage({ onClose }: { onClose: () => void }) {
  const session = useAuthStore((s) => s.session);
  const addToast = useUIStore((s) => s.addToast);

  const [tab, setTab] = useState<Tab>('users');
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    if (!session) return;
    setLoadingUsers(true);
    try {
      setUsers(await adminAPI.listUsers(session.accessToken));
    } catch {
      addToast('error', 'Failed to load users.');
    } finally {
      setLoadingUsers(false);
    }
  }, [session, addToast]);

  const loadLogs = useCallback(async () => {
    if (!session) return;
    setLoadingLogs(true);
    try {
      setLogs(await adminAPI.auditLogs(session.accessToken));
    } catch {
      addToast('error', 'Failed to load audit logs.');
    } finally {
      setLoadingLogs(false);
    }
  }, [session, addToast]);

  useEffect(() => { loadUsers(); }, [loadUsers]);
  useEffect(() => { if (tab === 'audit') loadLogs(); }, [tab, loadLogs]);

  async function doAction(
    action: () => Promise<{ message: string }>,
    id: string,
    successMsg: string,
  ) {
    setBusyId(id);
    try {
      await action();
      addToast('success', successMsg);
      await loadUsers();
    } catch (err: unknown) {
      addToast('error', (err as { detail?: string })?.detail ?? 'Action failed.');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="admin-overlay" onClick={onClose}>
      <div className="admin-panel glass-card" onClick={(e) => e.stopPropagation()}>
        {/* Panel header */}
        <div className="admin-header">
          <div className="admin-title">
            <ShieldIcon />
            <span>ADMIN CONSOLE</span>
          </div>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>

        {/* Tabs */}
        <div className="admin-tabs">
          <button
            className={`admin-tab ${tab === 'users' ? 'active' : ''}`}
            onClick={() => setTab('users')}
          >
            Users
          </button>
          <button
            className={`admin-tab ${tab === 'audit' ? 'active' : ''}`}
            onClick={() => setTab('audit')}
          >
            Audit Log
          </button>
        </div>

        {/* Users tab */}
        {tab === 'users' && (
          <div className="admin-content">
            {loadingUsers ? (
              <div className="admin-loading"><span className="spinner lg" /> Loading users…</div>
            ) : users.length === 0 ? (
              <div className="admin-empty">No users found.</div>
            ) : (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Email</th>
                      <th>Strikes</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className={u.is_banned ? 'row-banned' : ''}>
                        <td className="cell-email">{u.email}</td>
                        <td className="cell-strikes">
                          <span className={`strike-badge ${u.strike_count > 0 ? 'has-strikes' : ''}`}>
                            {u.strike_count}
                          </span>
                        </td>
                        <td>
                          {u.is_banned
                            ? <span className="status-badge banned">BANNED</span>
                            : <span className="status-badge active">ACTIVE</span>
                          }
                        </td>
                        <td className="cell-actions">
                          {u.is_banned ? (
                            <button
                              className="btn btn-xs btn-cyan"
                              disabled={busyId === u.id}
                              onClick={() =>
                                doAction(
                                  () => adminAPI.unbanUser(session!.accessToken, u.id),
                                  u.id,
                                  `${u.email} unbanned.`,
                                )
                              }
                            >
                              {busyId === u.id ? <span className="spinner" /> : null}
                              Unban
                            </button>
                          ) : (
                            <button
                              className="btn btn-xs btn-danger"
                              disabled={busyId === u.id}
                              onClick={() =>
                                doAction(
                                  () => adminAPI.banUser(session!.accessToken, u.id),
                                  u.id,
                                  `${u.email} banned.`,
                                )
                              }
                            >
                              {busyId === u.id ? <span className="spinner" /> : null}
                              Ban
                            </button>
                          )}
                          {u.strike_count > 0 && (
                            <button
                              className="btn btn-xs btn-purple"
                              disabled={busyId === u.id}
                              onClick={() =>
                                doAction(
                                  () => adminAPI.resetStrikes(session!.accessToken, u.id),
                                  u.id,
                                  `Strikes reset for ${u.email}.`,
                                )
                              }
                            >
                              Reset
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Audit log tab */}
        {tab === 'audit' && (
          <div className="admin-content">
            {loadingLogs ? (
              <div className="admin-loading"><span className="spinner lg" /> Loading logs…</div>
            ) : logs.length === 0 ? (
              <div className="admin-empty">No audit log entries.</div>
            ) : (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Type</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((lg) => (
                      <tr key={lg.id}>
                        <td className="cell-time">{formatTime(lg.timestamp)}</td>
                        <td>
                          <span className={`violation-badge vt-${lg.violation_type}`}>
                            {lg.violation_type}
                          </span>
                        </td>
                        <td className="cell-detail">{lg.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ShieldIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
