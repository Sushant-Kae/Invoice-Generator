'use client'

import { useState } from 'react'
import { Settings, Database, Globe, Shield, Info } from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export default function SettingsPage() {
  const [corsOrigins] = useState(API_BASE)

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 800, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Settings</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>System configuration and information</p>
        </div>

        {/* API Configuration */}
        <Section icon={Globe} title="API Configuration" color="var(--accent)">
          <Field label="Backend API URL" value={corsOrigins} mono />
          <Field label="Docs (Swagger)" value={`${API_BASE.replace('/api', '')}/api/docs`} mono />
        </Section>

        {/* Database */}
        <Section icon={Database} title="Database" color="var(--success)">
          <Field label="Engine" value="PostgreSQL (via SQLAlchemy)" />
          <Field label="ORM" value="SQLAlchemy 2.0 + Alembic migrations" />
        </Section>

        {/* Invoice Configuration */}
        <Section icon={Settings} title="Invoice Defaults" color="#a855f7">
          <Field label="Template" value="invoice_template.docx (Shah Enterprises)" />
          <Field label="Supported Upload Types" value="PDF, PNG, JPG, JPEG, WEBP" />
          <Field label="Max Upload Size" value="20 MB" />
          <Field label="PDF Conversion" value="LibreOffice headless (if installed)" />
        </Section>

        {/* Security note */}
        <Section icon={Shield} title="Data Privacy" color="var(--warning)">
          <InfoNote>
            Purchase rates, margin percentages, and estimated profit values are stored internally and are <strong>never exported</strong> in customer-facing invoices or DOCX files.
          </InfoNote>
        </Section>

        {/* App info */}
        <Section icon={Info} title="About" color="var(--text-muted)">
          <Field label="Application" value="Shah Enterprises Invoice Generator" />
          <Field label="Version" value="v2.0 — Internal Tool" />
          <Field label="Stack" value="Next.js 16 + FastAPI + PostgreSQL + python-docx" />
        </Section>
      </div>
    </AppLayout>
  )
}

// ─── Local helper sub-components ────────────────────────────────────

function Section({ icon: Icon, title, color, children }: { icon: any; title: string; color: string; children: React.ReactNode }) {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, marginBottom: 16, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 28, height: 28, borderRadius: 6, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={14} color={color} />
        </div>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{title}</span>
      </div>
      <div style={{ padding: '8px 0' }}>{children}</div>
    </div>
  )
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, padding: '10px 20px', borderBottom: '1px solid var(--border-subtle)' }}
      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500, minWidth: 180, flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)', fontFamily: mono ? 'monospace' : 'inherit', wordBreak: 'break-all' }}>{value}</span>
    </div>
  )
}

function InfoNote({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ margin: '10px 20px', padding: '10px 14px', background: 'var(--warning-muted, rgba(234,179,8,0.08))', border: '1px solid var(--warning, #ca8a04)', borderRadius: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
      {children}
    </div>
  )
}
