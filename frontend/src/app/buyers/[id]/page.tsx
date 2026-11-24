'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Download, FileText } from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'
import {
  getBuyer,
  getBuyerInvoices,
  getInvoiceDownloadUrl,
  type Buyer,
  type InvoiceListItem,
} from '@/lib/api'
import { formatCurrency } from '@/lib/utils'

export default function BuyerDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const buyerId = Number(id)
  const validBuyerId = Number.isSafeInteger(buyerId) && buyerId > 0

  const { data: buyer, isLoading: buyerLoading, isError: buyerError } = useQuery<Buyer>({
    queryKey: ['buyer', buyerId],
    queryFn: () => getBuyer(buyerId),
    enabled: validBuyerId,
    retry: 1,
  })

  const {
    data: invoices = [],
    isLoading: invoicesLoading,
    isError: invoicesError,
  } = useQuery<InvoiceListItem[]>({
    queryKey: ['buyer-invoices', buyerId],
    queryFn: () => getBuyerInvoices(buyerId),
    enabled: validBuyerId,
    retry: 1,
  })

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>
        <Link
          href="/buyers"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            marginBottom: 20,
            color: 'var(--text-secondary)',
            fontSize: 13,
            textDecoration: 'none',
          }}
        >
          <ArrowLeft size={14} /> Back to Buyers
        </Link>

        {!validBuyerId || buyerError ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--error)' }}>
            Buyer could not be loaded.
          </div>
        ) : buyerLoading || !buyer ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading buyer…
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 24 }}>
              <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>{buyer.name}</h1>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 24px', color: 'var(--text-secondary)', fontSize: 13 }}>
                {buyer.gst_number && <span>GST: {buyer.gst_number}</span>}
                {buyer.email && <span>{buyer.email}</span>}
                {buyer.phone && <span>{buyer.phone}</span>}
                {buyer.address && <span>{buyer.address}</span>}
              </div>
            </div>

            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', fontSize: 14, fontWeight: 600 }}>
                Invoices ({invoices.length})
              </div>

              {invoicesLoading ? (
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>Loading invoices…</div>
              ) : invoicesError ? (
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--error)' }}>Invoices could not be loaded.</div>
              ) : invoices.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  <FileText size={30} style={{ margin: '0 auto 10px', display: 'block' }} />
                  No invoices found for this buyer.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                        {['Invoice No.', 'Date', 'Total', 'Status', 'Downloads'].map((heading) => (
                          <th key={heading} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {invoices.map((invoice) => (
                        <tr key={invoice.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '11px 16px', color: 'var(--accent)', fontWeight: 600 }}>{invoice.invoice_number}</td>
                          <td style={{ padding: '11px 16px', color: 'var(--text-secondary)' }}>{invoice.invoice_date}</td>
                          <td style={{ padding: '11px 16px', fontWeight: 600 }}>{formatCurrency(invoice.total_amount)}</td>
                          <td style={{ padding: '11px 16px', color: 'var(--text-secondary)' }}>{invoice.status}</td>
                          <td style={{ padding: '11px 16px' }}>
                            <div style={{ display: 'flex', gap: 8 }}>
                              {invoice.docx_filename && (
                                <a
                                  href={getInvoiceDownloadUrl(invoice.id, 'docx')}
                                  download
                                  aria-label={`Download DOCX for ${invoice.invoice_number}`}
                                  style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 8px', background: 'var(--accent-muted)', color: 'var(--accent)', borderRadius: 4, textDecoration: 'none', fontSize: 11, fontWeight: 600 }}
                                >
                                  <Download size={11} /> DOCX
                                </a>
                              )}
                              {invoice.pdf_filename && (
                                <a
                                  href={getInvoiceDownloadUrl(invoice.id, 'pdf')}
                                  download
                                  aria-label={`Download PDF for ${invoice.invoice_number}`}
                                  style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 8px', background: 'var(--bg-hover)', color: 'var(--text-secondary)', borderRadius: 4, textDecoration: 'none', fontSize: 11, fontWeight: 600 }}
                                >
                                  <Download size={11} /> PDF
                                </a>
                              )}
                              {!invoice.docx_filename && !invoice.pdf_filename && (
                                <span style={{ color: 'var(--text-muted)' }}>—</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  )
}
