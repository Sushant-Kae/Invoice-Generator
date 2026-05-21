'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { FileText, Download, Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { AppLayout } from '@/components/layout/AppLayout'
import { getInvoices } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace('/api', '')

export default function HistoryPage() {
  const [search, setSearch] = useState('')

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices', 0, 100],
    queryFn: () => getInvoices(0, 100),
    retry: 1,
  })

  const filtered = (invoices as any[]).filter(
    (inv) =>
      inv.invoice_number.toLowerCase().includes(search.toLowerCase()) ||
      inv.buyer_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Invoice History</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>All generated invoices</p>
          </div>
          <Link
            href="/new-invoice"
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', background: 'var(--accent)', color: '#fff', borderRadius: 8, textDecoration: 'none', fontSize: 13, fontWeight: 600 }}
          >
            <Plus size={14} /> New Invoice
          </Link>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', marginBottom: 20, maxWidth: 400 }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search by invoice # or buyer…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px 9px 34px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--text-primary)',
              fontSize: 13,
              outline: 'none',
            }}
          />
        </div>

        {/* Table */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                {['Invoice No.', 'Buyer', 'Date', 'Items', 'Total', 'Status', 'Download'].map((h) => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <FileText size={32} style={{ margin: '0 auto 10px', display: 'block' }} />
                    {search ? 'No invoices match your search' : 'No invoices yet'}
                  </td>
                </tr>
              ) : (
                filtered.map((inv: any) => (
                  <tr key={inv.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.1s' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '11px 16px', fontWeight: 600, color: 'var(--accent)' }}>{inv.invoice_number}</td>
                    <td style={{ padding: '11px 16px' }}>{inv.buyer_name}</td>
                    <td style={{ padding: '11px 16px', color: 'var(--text-secondary)' }}>{inv.invoice_date}</td>
                    <td style={{ padding: '11px 16px', color: 'var(--text-secondary)' }}>{inv.items?.length ?? '—'}</td>
                    <td style={{ padding: '11px 16px', fontWeight: 600 }}>{formatCurrency(inv.total_amount)}</td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: inv.status === 'exported' ? 'var(--success-muted)' : inv.status === 'finalized' ? 'var(--accent-muted)' : 'var(--bg-hover)',
                        color: inv.status === 'exported' ? 'var(--success)' : inv.status === 'finalized' ? 'var(--accent)' : 'var(--text-secondary)',
                      }}>
                        {inv.status}
                      </span>
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {inv.docx_filename && (
                          <a href={`${API_BASE}/api/invoice/${inv.id}/download/docx`} download style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: 'var(--accent-muted)', color: 'var(--accent)', borderRadius: 4, textDecoration: 'none', fontSize: 11, fontWeight: 600 }}>
                            <Download size={11} /> DOCX
                          </a>
                        )}
                        {inv.pdf_filename && (
                          <a href={`${API_BASE}/api/invoice/${inv.id}/download/pdf`} download style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: 'var(--bg-hover)', color: 'var(--text-secondary)', borderRadius: 4, textDecoration: 'none', fontSize: 11, fontWeight: 600 }}>
                            <Download size={11} /> PDF
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  )
}
