'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import {
  TrendingUp, FileText, Plus, Clock, CheckCircle, FileUp,
  IndianRupee, BarChart3, WifiOff
} from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'
import { getDashboard, getInvoices } from '@/lib/api'
import type { DashboardStats, InvoiceListItem } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'

function StatCard({
  label, value, sub, icon: Icon, color = 'var(--accent)', loading = false,
}: {
  label: string; value: string; sub?: string; icon: any; color?: string; loading?: boolean
}) {
  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: '18px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
        <div
          style={{
            width: 32, height: 32, borderRadius: 8,
            background: `${color}22`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Icon size={15} color={color} />
        </div>
      </div>
      <div>
        {loading ? (
          <div style={{ height: 28, width: 80, background: 'var(--bg-hover)', borderRadius: 4, animation: 'pulse 1.5s ease-in-out infinite' }} />
        ) : (
          <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</p>
        )}
        {sub && !loading && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{sub}</p>
        )}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    retry: 2,
    staleTime: 30_000,
  })

  const { data: invoices = [], isLoading: invoicesLoading } = useQuery<InvoiceListItem[]>({
    queryKey: ['invoices-recent'],
    queryFn: () => getInvoices(0, 5),
    retry: 2,
    staleTime: 30_000,
    enabled: !statsError, // skip if backend is unreachable
  })

  const backendDown = !!statsError

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>

        {/* Page header */}
        <div
          style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 24, flexWrap: 'wrap', gap: 12,
          }}
        >
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Overview of invoice activity
            </p>
          </div>
          <Link
            href="/new-invoice"
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '9px 18px', background: 'var(--accent)', color: '#fff',
              borderRadius: 8, textDecoration: 'none', fontSize: 13, fontWeight: 600,
            }}
          >
            <Plus size={15} /> New Invoice
          </Link>
        </div>

        {/* Backend unreachable banner — only shown when API actually fails */}
        {backendDown && (
          <div
            className="animate-fade-in"
            style={{
              marginBottom: 20, padding: '12px 16px',
              background: 'var(--error-muted)', border: '1px solid var(--error)',
              borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
            }}
          >
            <WifiOff size={15} color="var(--error)" />
            <span>
              Cannot connect to backend at <strong>http://localhost:8000</strong>.
              Make sure <code style={{ background: 'rgba(0,0,0,0.3)', padding: '1px 4px', borderRadius: 3 }}>uvicorn</code> is running.
            </span>
          </div>
        )}

        {/* Stats grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 14, marginBottom: 28,
          }}
        >
          <StatCard
            label="Total Invoices"
            value={String(stats?.total_invoices ?? 0)}
            sub={`${stats?.monthly_invoices ?? 0} this month`}
            icon={FileText}
            color="var(--accent)"
            loading={statsLoading}
          />
          <StatCard
            label="Total Revenue"
            value={formatCurrency(stats?.total_revenue ?? 0)}
            sub={`${formatCurrency(stats?.monthly_revenue ?? 0)} this month`}
            icon={IndianRupee}
            color="var(--success)"
            loading={statsLoading}
          />
          <StatCard
            label="Estimated Profit"
            value={formatCurrency(stats?.estimated_profit ?? 0)}
            sub={`${formatCurrency(stats?.monthly_profit ?? 0)} this month`}
            icon={TrendingUp}
            color="#a855f7"
            loading={statsLoading}
          />
          <StatCard
            label="Invoice Status"
            value={`${stats?.finalized_count ?? 0} finalized`}
            sub={`${stats?.draft_count ?? 0} drafts`}
            icon={BarChart3}
            color="var(--warning)"
            loading={statsLoading}
          />
        </div>

        {/* Quick actions */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 12, marginBottom: 32,
          }}
        >
          {[
            { href: '/new-invoice', label: 'Create Invoice', sub: 'Upload & extract supplier PDF', icon: FileUp, color: 'var(--accent)' },
            { href: '/history',     label: 'View History',   sub: 'All generated invoices',        icon: Clock,  color: 'var(--success)' },
            { href: '/buyers',      label: 'Manage Buyers',  sub: 'Customer / buyer list',         icon: CheckCircle, color: '#a855f7' },
          ].map(({ href, label, sub, icon: Icon, color }) => (
            <Link
              key={href}
              href={href}
              style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '14px 18px',
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderRadius: 10, textDecoration: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = color)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
            >
              <div
                style={{
                  width: 38, height: 38, borderRadius: 8,
                  background: `${color}22`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}
              >
                <Icon size={17} color={color} />
              </div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{label}</p>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{sub}</p>
              </div>
            </Link>
          ))}
        </div>

        {/* Recent invoices table */}
        <div
          style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 10, overflow: 'hidden',
          }}
        >
          <div
            style={{
              padding: '14px 20px', borderBottom: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}
          >
            <span style={{ fontSize: 13, fontWeight: 600 }}>Recent Invoices</span>
            <Link href="/history" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
              View all →
            </Link>
          </div>

          {invoicesLoading ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Loading…
            </div>
          ) : invoices.length === 0 ? (
            <div style={{ padding: '40px 24px', textAlign: 'center' }}>
              <FileText size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px', display: 'block' }} />
              <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No invoices yet</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                Create your first invoice to get started.
              </p>
              <Link
                href="/new-invoice"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '9px 18px', background: 'var(--accent)', color: '#fff',
                  borderRadius: 8, textDecoration: 'none', fontSize: 13, fontWeight: 600,
                }}
              >
                <Plus size={14} /> Create Invoice
              </Link>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: 'var(--bg-surface)' }}>
                  {['Invoice No.', 'Buyer', 'Date', 'Total', 'Status'].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '9px 16px', textAlign: 'left',
                        fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                        borderBottom: '1px solid var(--border)',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.1s' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--accent)' }}>
                      {inv.invoice_number}
                    </td>
                    <td style={{ padding: '10px 16px' }}>{inv.buyer_name}</td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>
                      {inv.invoice_date}
                    </td>
                    <td style={{ padding: '10px 16px', fontWeight: 600 }}>
                      {formatCurrency(inv.total_amount)}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <StatusBadge status={inv.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppLayout>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string }> = {
    exported:  { bg: 'var(--success-muted)', color: 'var(--success)' },
    finalized: { bg: 'var(--accent-muted)',  color: 'var(--accent)' },
    draft:     { bg: 'var(--bg-hover)',       color: 'var(--text-secondary)' },
  }
  const s = styles[status] ?? styles.draft
  return (
    <span
      style={{
        padding: '2px 8px', borderRadius: 4,
        fontSize: 11, fontWeight: 600,
        background: s.bg, color: s.color,
      }}
    >
      {status}
    </span>
  )
}