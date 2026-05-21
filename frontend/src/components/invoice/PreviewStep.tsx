'use client'

import { useState } from 'react'
import { ChevronLeft, FileCheck2, Loader2, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { createInvoice, generateInvoice } from '@/lib/api'
import type { InvoiceCreate } from '@/lib/api'
import { useInvoiceStore } from '@/store/invoiceStore'
import { formatCurrency } from '@/lib/utils'

export function PreviewStep() {
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    extractedItems,
    invoiceNumber, invoiceDate, buyerName, buyerGst,
    taxMode, cgstPercent, sgstPercent, igstPercent,
    getSubtotal, getTaxAmount, getTotalAmount,
    setGeneratedResult, setStep,
  } = useInvoiceStore()

  const subtotal = getSubtotal()
  const taxAmount = getTaxAmount()
  const total = getTotalAmount()

  const handleGenerate = async () => {
    if (!buyerName.trim()) { toast.error('Buyer name is required'); return }
    if (!invoiceNumber.trim()) { toast.error('Invoice number is required'); return }
    if (extractedItems.length === 0) { toast.error('No items to invoice'); return }

    setError(null)
    setGenerating(true)

    try {
      // Build payload matching InvoiceCreate schema exactly
      const payload: InvoiceCreate = {
        invoice_number: invoiceNumber,
        invoice_date: invoiceDate,
        buyer_name: buyerName,
        buyer_gst: buyerGst?.trim() || undefined,
        tax_mode: taxMode,
        cgst_percent: cgstPercent,
        sgst_percent: sgstPercent,
        igst_percent: igstPercent,
        items: extractedItems.map((item) => ({
          sr_no: item.sr_no,
          item_name: item.item_name,
          hsn_code: item.hsn_code,
          qty: item.qty,
          unit: item.unit || 'Nos',
          purchase_rate: item.purchase_rate,
          margin_percent: item.margin_percent,
          selling_rate: item.selling_rate,
          amount: item.amount,
          estimated_profit: item.estimated_profit,
        })),
      }

      // 1. Create invoice record in DB
      const created = await createInvoice(payload)

      // 2. Generate DOCX + PDF
      const generated = await generateInvoice(created.id, 'both')

      if (!generated.success) {
        throw new Error(generated.message || 'Generation failed')
      }

      setGeneratedResult(
        created.id,
        generated.docx_url ?? undefined,
        generated.pdf_url ?? undefined,
      )

      setStep('done')
      toast.success('Invoice generated successfully!')
    } catch (err: any) {
      const msg = err.message || 'Invoice generation failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setGenerating(false)
    }
  }

  const taxLabel =
    taxMode === 'igst'      ? `IGST @ ${igstPercent}%` :
    taxMode === 'cgst_sgst' ? `CGST ${cgstPercent}% + SGST ${sgstPercent}%` :
                              'No Tax'

  return (
    <div style={{ maxWidth: 780, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Invoice Preview</h2>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Review before generating the final invoice document.
        </p>
      </div>

      {/* Preview card */}
      <div
        style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 12, overflow: 'hidden',
        }}
      >
        {/* Invoice header bar */}
        <div
          style={{
            padding: '20px 24px',
            background: 'linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%)',
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'flex-start', flexWrap: 'wrap', gap: 12,
          }}
        >
          <div>
            <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)', marginBottom: 3, letterSpacing: '0.1em' }}>
              TAX INVOICE
            </p>
            <h3 style={{ fontSize: 20, fontWeight: 700, color: '#fff' }}>Shah Enterprises</h3>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>{invoiceNumber}</p>
            <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>{invoiceDate}</p>
          </div>
        </div>

        {/* Buyer + tax info */}
        <div
          style={{
            padding: '16px 24px', borderBottom: '1px solid var(--border)',
            display: 'flex', gap: 40, flexWrap: 'wrap',
          }}
        >
          <div>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 5 }}>
              Bill To
            </p>
            <p style={{ fontSize: 14, fontWeight: 600 }}>{buyerName || '—'}</p>
            {buyerGst && (
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                GST: {buyerGst}
              </p>
            )}
          </div>
          <div>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 5 }}>
              Tax
            </p>
            <p style={{ fontSize: 13, fontWeight: 600 }}>{taxLabel}</p>
          </div>
          <div>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 5 }}>
              Items
            </p>
            <p style={{ fontSize: 13, fontWeight: 600 }}>{extractedItems.length}</p>
          </div>
        </div>

        {/* Items table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                {[
                  { label: '#',           align: 'left'  },
                  { label: 'Description', align: 'left'  },
                  { label: 'HSN',         align: 'left'  },
                  { label: 'Qty',         align: 'right' },
                  { label: 'Rate',        align: 'right' },
                  { label: 'Amount',      align: 'right' },
                ].map(({ label, align }) => (
                  <th
                    key={label}
                    style={{
                      padding: '9px 14px',
                      textAlign: align as any,
                      fontSize: 11, color: 'var(--text-secondary)',
                      fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em',
                    }}
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {extractedItems.map((item, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>{item.sr_no}</td>
                  <td style={{ padding: '10px 14px', fontWeight: 500, maxWidth: 260 }}>
                    {item.item_name}
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>
                    {item.hsn_code || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                    {item.qty} {item.unit || ''}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                    ₹{item.selling_rate.toFixed(2)}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 600 }}>
                    ₹{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals */}
        <div
          style={{
            padding: '16px 24px', borderTop: '1px solid var(--border)',
            display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6,
          }}
        >
          <TotalRow label="Subtotal" value={formatCurrency(subtotal)} />
          <TotalRow label={taxLabel} value={formatCurrency(taxAmount)} />
          <TotalRow label="Total" value={formatCurrency(total)} bold />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: '12px 16px',
            background: 'var(--error-muted)', border: '1px solid var(--error)',
            borderRadius: 8, display: 'flex', alignItems: 'flex-start', gap: 10,
          }}
        >
          <AlertCircle size={16} color="var(--error)" style={{ marginTop: 1 }} />
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--error)', marginBottom: 2 }}>
              Generation failed
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{error}</p>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 4 }}>
        <button
          onClick={() => setStep('review')}
          disabled={generating}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '9px 18px',
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 8, color: 'var(--text-secondary)',
            cursor: generating ? 'not-allowed' : 'pointer', fontSize: 13,
          }}
        >
          <ChevronLeft size={15} /> Back
        </button>

        <button
          id="generate-invoice-btn"
          onClick={handleGenerate}
          disabled={generating}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '9px 22px',
            background: generating ? 'var(--bg-hover)' : 'var(--accent)',
            border: 'none', borderRadius: 8,
            color: generating ? 'var(--text-muted)' : '#fff',
            cursor: generating ? 'not-allowed' : 'pointer',
            fontSize: 13, fontWeight: 600,
          }}
        >
          {generating
            ? <><Loader2 size={15} className="animate-spin" /> Generating…</>
            : <><FileCheck2 size={15} /> Generate Invoice</>
          }
        </button>
      </div>
    </div>
  )
}

function TotalRow({ label, value, bold = false }: { label: string; value: string; bold?: boolean }) {
  return (
    <div
      style={{
        display: 'flex', gap: 48,
        ...(bold ? { borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 4 } : {}),
      }}
    >
      <span style={{ fontSize: bold ? 14 : 12, color: 'var(--text-secondary)' }}>{label}</span>
      <span
        style={{
          minWidth: 130, textAlign: 'right',
          fontSize: bold ? 17 : 13, fontWeight: bold ? 700 : 500,
          color: bold ? 'var(--text-primary)' : 'var(--text-secondary)',
        }}
      >
        {value}
      </span>
    </div>
  )
}
