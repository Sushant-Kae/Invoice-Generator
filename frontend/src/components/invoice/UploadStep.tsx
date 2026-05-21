'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadInvoice, extractInvoice, applyMargin } from '@/lib/api'
import type { ExtractionResult } from '@/lib/api'
import { useInvoiceStore } from '@/store/invoiceStore'
import type { InvoiceItem } from '@/store/invoiceStore'

type LoadingPhase = 'idle' | 'uploading' | 'extracting' | 'applying-margin'

const PHASE_LABELS: Record<LoadingPhase, string> = {
  idle:             '',
  uploading:        'Uploading file…',
  extracting:       'Extracting data from invoice…',
  'applying-margin': 'Calculating selling rates…',
}

export function UploadStep() {
  const [phase, setPhase] = useState<LoadingPhase>('idle')
  const [error, setError] = useState<string | null>(null)

  const { setUploadedFile, setExtractionResult, setStep, globalMargin } = useInvoiceStore()

  const processFile = useCallback(
    async (file: File) => {
      setError(null)

      // ── Phase 1: Upload ──────────────────────────────
      setPhase('uploading')
      let uploadRes
      try {
        uploadRes = await uploadInvoice(file)
      } catch (err: any) {
        setError(err.message || 'Upload failed')
        setPhase('idle')
        toast.error(err.message || 'Upload failed')
        return
      }

      const { file_id, filename } = uploadRes
      setUploadedFile(file_id, filename)

      // ── Phase 2: Extract ─────────────────────────────
      setPhase('extracting')
      let extractRes: ExtractionResult
      try {
        extractRes = await extractInvoice(file_id)
      } catch (err: any) {
        setError(err.message || 'Extraction failed')
        setPhase('idle')
        toast.error(err.message || 'Extraction failed')
        return
      }

      if (!extractRes.success) {
        const msg = extractRes.warnings.join('; ') || 'Extraction returned no data'
        setError(msg)
        setPhase('idle')
        toast.error(msg)
        return
      }

      // ── Phase 3: Apply margin via backend ────────────
      setPhase('applying-margin')
      let finalItems: InvoiceItem[]

      try {
        // Backend ExtractedItem has no selling_rate yet — send them through /apply-margin
        const marginRes = await applyMargin({
          items: extractRes.items,
          global_margin_percent: globalMargin,
          round_values: true,
        })

        finalItems = marginRes.items.map((item, i) => ({
          sr_no: i + 1,
          item_name: item.item_name,
          hsn_code: item.hsn_code ?? null,
          qty: item.qty,
          unit: item.unit ?? 'Nos',
          purchase_rate: item.purchase_rate,
          margin_percent: item.margin_percent,
          selling_rate: item.selling_rate,
          amount: item.amount,
          estimated_profit: (item.selling_rate - item.purchase_rate) * item.qty,
        }))
      } catch {
        // /apply-margin failed — compute client-side as fallback
        finalItems = extractRes.items.map((item, i) => {
          const sellingRate = parseFloat(
            (item.purchase_rate * (1 + globalMargin / 100)).toFixed(2)
          )
          const amount = parseFloat((sellingRate * item.qty).toFixed(2))
          return {
            sr_no: i + 1,
            item_name: item.item_name,
            hsn_code: item.hsn_code ?? null,
            qty: item.qty,
            unit: item.unit ?? 'Nos',
            purchase_rate: item.purchase_rate,
            margin_percent: globalMargin,
            selling_rate: sellingRate,
            amount,
            estimated_profit: parseFloat(((sellingRate - item.purchase_rate) * item.qty).toFixed(2)),
          }
        })
      }

      setExtractionResult(
        finalItems,
        extractRes.method,
        Math.round(extractRes.confidence),
        extractRes.warnings
      )

      setPhase('idle')
      setStep('review')
      toast.success(`Extracted ${finalItems.length} item${finalItems.length !== 1 ? 's' : ''}`)
    },
    [setUploadedFile, setExtractionResult, setStep, globalMargin]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => accepted[0] && processFile(accepted[0]),
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
    },
    maxFiles: 1,
    disabled: phase !== 'idle',
  })

  const busy = phase !== 'idle'

  return (
    <div style={{ maxWidth: 680, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
          Upload Supplier Invoice
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Upload a PDF or image of the manufacturer's invoice. Data will be extracted automatically.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        style={{
          border: `2px dashed ${isDragActive ? 'var(--accent)' : error ? 'var(--error)' : 'var(--border)'}`,
          borderRadius: 12,
          padding: '52px 32px',
          textAlign: 'center',
          cursor: busy ? 'not-allowed' : 'pointer',
          background: isDragActive ? 'var(--accent-muted)' : 'var(--bg-card)',
          transition: 'all 0.2s ease',
        }}
      >
        <input {...getInputProps()} />

        {busy ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
            <Loader2 size={40} color="var(--accent)" className="animate-spin" />
            <div>
              <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                {PHASE_LABELS[phase]}
              </p>
              {phase === 'extracting' && (
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  This may take 10–30 seconds for complex invoices
                </p>
              )}
            </div>
            {/* Progress dots */}
            <div style={{ display: 'flex', gap: 6 }}>
              {(['uploading', 'extracting', 'applying-margin'] as LoadingPhase[]).map((p) => (
                <div
                  key={p}
                  style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background:
                      phase === p ? 'var(--accent)' :
                      (['uploading', 'extracting', 'applying-margin'] as LoadingPhase[]).indexOf(p) <
                      (['uploading', 'extracting', 'applying-margin'] as LoadingPhase[]).indexOf(phase)
                        ? 'var(--success)'
                        : 'var(--border)',
                    transition: 'background 0.3s',
                  }}
                />
              ))}
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 64, height: 64, borderRadius: 14,
                background: isDragActive ? 'var(--accent)' : 'var(--accent-muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s ease',
              }}
            >
              {isDragActive
                ? <CheckCircle2 size={30} color="#fff" />
                : <Upload size={28} color="var(--accent)" />
              }
            </div>
            <div>
              <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                {isDragActive ? 'Drop to upload' : 'Drag & drop your invoice here'}
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                or{' '}
                <span style={{ color: 'var(--accent)', textDecoration: 'underline', cursor: 'pointer' }}>
                  browse files
                </span>
              </p>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              PDF, JPG, PNG, WEBP · Max 20 MB
            </p>
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: 16, padding: '12px 16px',
            background: 'var(--error-muted)', border: '1px solid var(--error)',
            borderRadius: 8, display: 'flex', alignItems: 'flex-start', gap: 10,
          }}
        >
          <AlertCircle size={16} color="var(--error)" style={{ marginTop: 1, flexShrink: 0 }} />
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--error)', marginBottom: 2 }}>
              Processing failed
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{error}</p>
          </div>
        </div>
      )}

      {/* Tips */}
      <div
        style={{
          marginTop: 24, padding: 16,
          background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border-subtle)',
        }}
      >
        <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
          Tips for accurate extraction
        </p>
        {[
          'Use digital PDFs or high-resolution scans (300 dpi+)',
          'Ensure the product table is fully visible and not cropped',
          'GST summary rows are automatically excluded from item extraction',
          'Multi-line product descriptions are merged automatically',
        ].map((tip) => (
          <div key={tip} style={{ display: 'flex', alignItems: 'flex-start', gap: 7, marginBottom: 7 }}>
            <FileText size={12} color="var(--text-muted)" style={{ marginTop: 2, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{tip}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
