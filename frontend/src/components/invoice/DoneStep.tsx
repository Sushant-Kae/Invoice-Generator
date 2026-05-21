'use client'

import { CheckCircle2, Download, Plus, FileCode2, FileText, ExternalLink } from 'lucide-react'
import { useInvoiceStore } from '@/store/invoiceStore'
import { getInvoiceDownloadUrl } from '@/lib/api'

export function DoneStep() {
  const { docxUrl, pdfUrl, invoiceNumber, generatedInvoiceId, reset } = useInvoiceStore()

  /**
   * Build a download link. The backend returns URLs in two forms:
   *   "/generated/<filename>"   — served as a static mount
   *   null                       — file wasn't generated
   *
   * We use the typed download endpoint so downloads always work regardless
   * of how the backend constructed the URL.
   */
  const docxHref = generatedInvoiceId
    ? getInvoiceDownloadUrl(generatedInvoiceId, 'docx')
    : docxUrl ?? undefined

  const pdfHref = generatedInvoiceId
    ? getInvoiceDownloadUrl(generatedInvoiceId, 'pdf')
    : pdfUrl ?? undefined

  const hasDocx = !!docxUrl
  const hasPdf  = !!pdfUrl

  return (
    <div
      style={{
        maxWidth: 540, margin: '0 auto', textAlign: 'center',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 24, paddingTop: 16,
      }}
    >
      {/* Success indicator */}
      <div
        className="animate-pulse-glow"
        style={{
          width: 76, height: 76, borderRadius: '50%',
          background: 'var(--success-muted)', border: '2px solid var(--success)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        <CheckCircle2 size={38} color="var(--success)" />
      </div>

      <div>
        <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
          Invoice Generated!
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          <strong style={{ color: 'var(--text-primary)' }}>{invoiceNumber}</strong>
          {' '}has been saved and is ready to download.
        </p>
      </div>

      {/* Download buttons */}
      {(hasDocx || hasPdf) ? (
        <div
          style={{
            display: 'flex', gap: 12, flexWrap: 'wrap',
            justifyContent: 'center', width: '100%',
          }}
        >
          {hasDocx && docxHref && (
            <a
              id="download-docx-btn"
              href={docxHref}
              download
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '11px 22px',
                background: 'var(--accent)', color: '#fff',
                borderRadius: 8, textDecoration: 'none',
                fontSize: 13, fontWeight: 600,
              }}
            >
              <FileCode2 size={15} /> Download DOCX
            </a>
          )}
          {hasPdf && pdfHref && (
            <a
              id="download-pdf-btn"
              href={pdfHref}
              download
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '11px 22px',
                background: 'var(--bg-card)', color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 8, textDecoration: 'none',
                fontSize: 13, fontWeight: 600,
              }}
            >
              <FileText size={15} /> Download PDF
            </a>
          )}
        </div>
      ) : (
        <div
          style={{
            padding: '14px 20px',
            background: 'var(--warning-muted)', border: '1px solid var(--warning)',
            borderRadius: 8, fontSize: 13, color: 'var(--text-primary)', maxWidth: 420,
          }}
        >
          Invoice was saved but file generation encountered an issue.
          Check the backend logs or try regenerating from History.
        </div>
      )}

      {/* View in history */}
      {generatedInvoiceId && (
        <a
          href="/history"
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 12, color: 'var(--accent)', textDecoration: 'none',
          }}
        >
          <ExternalLink size={13} /> View in Invoice History
        </a>
      )}

      {/* New invoice */}
      <button
        onClick={reset}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '9px 20px',
          background: 'transparent', border: '1px solid var(--border)',
          borderRadius: 8, color: 'var(--text-secondary)',
          cursor: 'pointer', fontSize: 13, marginTop: 4,
        }}
      >
        <Plus size={14} /> Create Another Invoice
      </button>
    </div>
  )
}
