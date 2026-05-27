'use client'

import { useQuery } from '@tanstack/react-query'
import { TrendingUp, IndianRupee, Package, BarChart3 } from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'
import { getInvoices } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import type { InvoiceListItem } from '@/lib/api'

export default function ProfitPage() {
  const { data: invoices = [], isLoading } = useQuery<InvoiceListItem[]>({
    queryKey: ['invoices', 0, 200],
    queryFn: () => getInvoices(0, 200),
    retry: 1,
  })

  // Aggregate profit metrics from invoice list
  const totalRevenue = invoices.reduce((sum, inv) => sum + (inv.total_amount ?? 0), 0)
  const totalProfit = invoices.reduce((sum, inv) => sum + (inv.estimated_profit ?? 0), 0)
  const avgMargin = totalRevenue > 0 ? (totalProfit / totalRevenue) * 100 : 0
  const exportedCount = invoices.filter((inv) => inv.status === 'exported').length

  const stats = [
    { label: 'Total Revenue', value: formatCurrency(totalRevenue), icon: IndianRupee, color: 'var(--success)' },
    { label: 'Estimated Profit', value: formatCurrency(totalProfit), icon: TrendingUp, color: '#a855f7' },
    { label: 'Avg. Margin', value: `${avgMargin.toFixed(1)}%`, icon: BarChart3, color: 'var(--accent)' },
    { label: 'Exported Invoices', value: String(exportedCount), icon: Package, color: 'var(--warning)' },
  ]

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Profit Overview</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Internal margin and profit summary — never exported to customers</p>
        </div>

        {/* Stats grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 14, marginBottom: 32 }}>
          {stats.map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon size={15} color={color} />
                </div>
              </div>
              {isLoading ? (
                <div style={{ height: 28, width: 80, background: 'var(--bg-hover)', borderRadius: 4 }} />
              ) : (
                <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</p>
              )}
            </div>
          ))}
        </div>

        {/* Per-invoice profit table */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Invoice Profit Breakdown</span>
          </div>
          {isLoading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
          ) : invoices.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center' }}>
              <TrendingUp size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px', display: 'block' }} />
              <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No invoices yet</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Create invoices to see profit analysis here.</p>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                  {['Invoice No.', 'Buyer', 'Date', 'Revenue', 'Est. Profit', 'Status'].map((h) => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
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
                    <td style={{ padding: '11px 16px', fontWeight: 600, color: 'var(--accent)' }}>{inv.invoice_number}</td>
                    <td style={{ padding: '11px 16px' }}>{inv.buyer_name}</td>
                    <td style={{ padding: '11px 16px', color: 'var(--text-secondary)' }}>{inv.invoice_date}</td>
                    <td style={{ padding: '11px 16px', fontWeight: 600 }}>{formatCurrency(inv.total_amount)}</td>
                    <td style={{ padding: '11px 16px', color: 'var(--success)', fontWeight: 600 }}>
                      {formatCurrency(inv.estimated_profit ?? 0)}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: inv.status === 'exported' ? 'var(--success-muted)' : inv.status === 'finalized' ? 'var(--accent-muted)' : 'var(--bg-hover)',
                        color: inv.status === 'exported' ? 'var(--success)' : inv.status === 'finalized' ? 'var(--accent)' : 'var(--text-secondary)',
                      }}>
                        {inv.status}
                      </span>
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
