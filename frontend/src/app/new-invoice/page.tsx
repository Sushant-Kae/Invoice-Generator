'use client'

import { AppLayout } from '@/components/layout/AppLayout'
import { UploadStep } from '@/components/invoice/UploadStep'
import { ReviewStep } from '@/components/invoice/ReviewStep'
import { PreviewStep } from '@/components/invoice/PreviewStep'
import { DoneStep } from '@/components/invoice/DoneStep'
import { useInvoiceStore } from '@/store/invoiceStore'
import { Upload, ClipboardList, Eye, CheckCircle2 } from 'lucide-react'

const STEPS = [
  { key: 'upload',  label: 'Upload',   icon: Upload },
  { key: 'review',  label: 'Review',   icon: ClipboardList },
  { key: 'preview', label: 'Preview',  icon: Eye },
  { key: 'done',    label: 'Done',     icon: CheckCircle2 },
] as const

export default function NewInvoicePage() {
  const step = useInvoiceStore((s) => s.step)
  const currentIdx = STEPS.findIndex((s) => s.key === step)

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>
        {/* Step progress bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 40 }}>
          {STEPS.map(({ key, label, icon: Icon }, i) => {
            const isDone = i < currentIdx
            const isActive = i === currentIdx
            return (
              <div key={key} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : 0 }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: '50%',
                      background: isDone ? 'var(--success)' : isActive ? 'var(--accent)' : 'var(--bg-card)',
                      border: `2px solid ${isDone ? 'var(--success)' : isActive ? 'var(--accent)' : 'var(--border)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <Icon size={15} color={isDone || isActive ? '#fff' : 'var(--text-muted)'} />
                  </div>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? 'var(--text-primary)' : isDone ? 'var(--success)' : 'var(--text-muted)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    style={{
                      flex: 1,
                      height: 2,
                      background: i < currentIdx ? 'var(--success)' : 'var(--border)',
                      margin: '0 8px',
                      marginBottom: 22,
                      transition: 'background 0.3s ease',
                    }}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Step content */}
        <div className="animate-fade-in">
          {step === 'upload'  && <UploadStep />}
          {step === 'review'  && <ReviewStep />}
          {step === 'preview' && <PreviewStep />}
          {step === 'done'    && <DoneStep />}
        </div>
      </div>
    </AppLayout>
  )
}
