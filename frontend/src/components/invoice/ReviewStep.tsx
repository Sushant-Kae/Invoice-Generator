'use client'

import { useState } from 'react'
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Percent,
  TrendingUp,
  Package,
  Info,
} from 'lucide-react'
import { useInvoiceStore } from '@/store/invoiceStore'
import type { InvoiceItem } from '@/store/invoiceStore'
import { formatCurrency, confidenceColor, confidenceLabel } from '@/lib/utils'

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-primary)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  color: 'var(--text-primary)',
  fontSize: 12,
  padding: '4px 8px',
  width: '100%',
  outline: 'none',
}

function EditableCell({
  value,
  field,
  index,
  type = 'text',
}: {
  value: string | number
  field: keyof InvoiceItem
  index: number
  type?: 'text' | 'number'
}) {
  const updateItem = useInvoiceStore((s) => s.updateItem)
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => updateItem(index, field, type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)}
      style={inputStyle}
    />
  )
}

export function ReviewStep() {
  const {
    extractedItems,
    extractionConfidence,
    extractionMethod,
    extractionWarnings,
    globalMargin,
    taxMode,
    cgstPercent,
    sgstPercent,
    igstPercent,
    invoiceNumber,
    invoiceDate,
    buyerName,
    buyerGst,
    getSubtotal,
    getTaxAmount,
    getTotalAmount,
    applyGlobalMargin,
    setInvoiceField,
    setStep,
  } = useInvoiceStore()

  const [marginInput, setMarginInput] = useState(String(globalMargin))

  const subtotal = getSubtotal()
  const taxAmount = getTaxAmount()
  const total = getTotalAmount()

  const handleApplyMargin = () => {
    const m = parseFloat(marginInput)
    if (!isNaN(m) && m >= 0) {
      setInvoiceField('globalMargin', m)
      applyGlobalMargin()
    }
  }

  const confidenceCol = confidenceColor(extractionConfidence)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Review Extracted Items</h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Edit any fields before generating the final invoice.
          </p>
        </div>

        {/* Confidence badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 14px',
            background: 'var(--bg-card)',
            border: `1px solid ${confidenceCol}`,
            borderRadius: 20,
          }}
        >
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: confidenceCol }} />
          <span style={{ fontSize: 12, color: confidenceCol, fontWeight: 600 }}>
            {confidenceLabel(extractionConfidence)} Confidence — {extractionConfidence}%
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>via {extractionMethod}</span>
        </div>
      </div>

      {/* Warnings */}
      {extractionWarnings.length > 0 && (
        <div
          style={{
            padding: '10px 14px',
            background: 'var(--warning-muted)',
            border: '1px solid var(--warning)',
            borderRadius: 8,
            display: 'flex',
            gap: 10,
          }}
        >
          <AlertTriangle size={16} color="var(--warning)" style={{ marginTop: 1, flexShrink: 0 }} />
          <div>
            {extractionWarnings.map((w, i) => (
              <p key={i} style={{ fontSize: 12, color: 'var(--text-primary)' }}>{w}</p>
            ))}
          </div>
        </div>
      )}

      {/* Invoice Details */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: 20,
        }}
      >
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Invoice Details
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
          {[
            { label: 'Invoice Number', field: 'invoiceNumber' as const, value: invoiceNumber },
            { label: 'Invoice Date', field: 'invoiceDate' as const, value: invoiceDate, type: 'date' },
            { label: 'Buyer Name', field: 'buyerName' as const, value: buyerName },
            { label: 'Buyer GST', field: 'buyerGst' as const, value: buyerGst },
          ].map(({ label, field, value, type }) => (
            <div key={field}>
              <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                {label}
              </label>
              <input
                type={type || 'text'}
                value={value}
                onChange={(e) => setInvoiceField(field, e.target.value)}
                style={{ ...inputStyle, padding: '7px 10px', fontSize: 13 }}
                placeholder={`Enter ${label.toLowerCase()}`}
              />
            </div>
          ))}
        </div>

        {/* Tax mode */}
        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Tax Mode</label>
            <select
              value={taxMode}
              onChange={(e) => setInvoiceField('taxMode', e.target.value as any)}
              style={{ ...inputStyle, padding: '7px 10px', fontSize: 13, width: 'auto', cursor: 'pointer' }}
            >
              <option value="igst">IGST</option>
              <option value="cgst_sgst">CGST + SGST</option>
              <option value="none">No Tax</option>
            </select>
          </div>
          {taxMode === 'igst' && (
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>IGST %</label>
              <input
                type="number"
                value={igstPercent}
                onChange={(e) => setInvoiceField('igstPercent', parseFloat(e.target.value))}
                style={{ ...inputStyle, padding: '7px 10px', fontSize: 13, width: 80 }}
              />
            </div>
          )}
          {taxMode === 'cgst_sgst' && (
            <>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>CGST %</label>
                <input type="number" value={cgstPercent} onChange={(e) => setInvoiceField('cgstPercent', parseFloat(e.target.value))} style={{ ...inputStyle, padding: '7px 10px', fontSize: 13, width: 80 }} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>SGST %</label>
                <input type="number" value={sgstPercent} onChange={(e) => setInvoiceField('sgstPercent', parseFloat(e.target.value))} style={{ ...inputStyle, padding: '7px 10px', fontSize: 13, width: 80 }} />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Global Margin */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          flexWrap: 'wrap',
        }}
      >
        <Percent size={16} color="var(--accent)" />
        <div style={{ flex: 1, minWidth: 200 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
            Global Margin
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Apply the same margin % to all items at once
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="number"
            value={marginInput}
            onChange={(e) => setMarginInput(e.target.value)}
            style={{ ...inputStyle, width: 80, padding: '7px 10px', fontSize: 14 }}
            min={0}
            max={200}
            step={0.5}
          />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>%</span>
          <button
            onClick={handleApplyMargin}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 14px',
              background: 'var(--accent)',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            <RefreshCw size={13} />
            Apply
          </button>
        </div>
      </div>

      {/* Items Table */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Package size={15} color="var(--text-secondary)" />
          <span style={{ fontSize: 13, fontWeight: 600 }}>
            {extractedItems.length} Extracted Items
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                {['#', 'Item Name', 'HSN', 'Qty', 'Unit', 'Purchase Rate', 'Margin %', 'Selling Rate', 'Amount'].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: '9px 12px',
                      textAlign: h === '#' ? 'center' : 'left',
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {extractedItems.map((item, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '8px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {item.sr_no}
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: 200 }}>
                    <EditableCell value={item.item_name} field="item_name" index={idx} />
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: 90 }}>
                    <EditableCell value={item.hsn_code || ''} field="hsn_code" index={idx} />
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: 70 }}>
                    <EditableCell value={item.qty} field="qty" index={idx} type="number" />
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: 70 }}>
                    <EditableCell value={item.unit || ''} field="unit" index={idx} />
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: 100 }}>
                    <EditableCell value={item.purchase_rate} field="purchase_rate" index={idx} type="number" />
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: 80 }}>
                    <EditableCell value={item.margin_percent} field="margin_percent" index={idx} type="number" />
                  </td>
                  <td style={{ padding: '8px 12px', minWidth: 100 }}>
                    <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                      ₹{item.selling_rate.toFixed(2)}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px', minWidth: 110, fontWeight: 600 }}>
                    ₹{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals footer */}
        <div
          style={{
            padding: '14px 20px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 24,
          }}
        >
          {[
            { label: 'Subtotal', value: formatCurrency(subtotal) },
            { label: `Tax (${taxMode === 'igst' ? `IGST ${igstPercent}%` : taxMode === 'cgst_sgst' ? `${cgstPercent + sgstPercent}%` : 'None'})`, value: formatCurrency(taxAmount) },
            { label: 'Total', value: formatCurrency(total), bold: true },
          ].map(({ label, value, bold }) => (
            <div key={label} style={{ textAlign: 'right' }}>
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</p>
              <p style={{ fontSize: bold ? 16 : 14, fontWeight: bold ? 700 : 500, color: bold ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                {value}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Profit indicator */}
      <div
        style={{
          padding: '12px 16px',
          background: 'var(--success-muted)',
          border: '1px solid var(--success)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <TrendingUp size={16} color="var(--success)" />
        <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
          Estimated profit:{' '}
          <strong>
            {formatCurrency(extractedItems.reduce((s, i) => s + i.estimated_profit, 0))}
          </strong>
          {' '}(internal only — not shown on invoice)
        </span>
        <Info size={14} color="var(--text-muted)" style={{ marginLeft: 'auto' }} />
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 4 }}>
        <button
          onClick={() => setStep('upload')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '9px 18px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          <ChevronLeft size={15} /> Back
        </button>
        <button
          onClick={() => setStep('preview')}
          disabled={extractedItems.length === 0}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '9px 20px',
            background: extractedItems.length > 0 ? 'var(--accent)' : 'var(--bg-hover)',
            border: 'none',
            borderRadius: 8,
            color: extractedItems.length > 0 ? '#fff' : 'var(--text-muted)',
            cursor: extractedItems.length > 0 ? 'pointer' : 'not-allowed',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Continue to Preview <ChevronRight size={15} />
        </button>
      </div>
    </div>
  )
}
