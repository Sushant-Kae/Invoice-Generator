'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Users, Plus, X, Phone, Mail, MapPin, Hash } from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'
import { getBuyers, createBuyer } from '@/lib/api'
import type { Buyer, BuyerCreate } from '@/lib/api'

export default function BuyersPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<BuyerCreate>({ name: '', gst_number: '', address: '', email: '', phone: '' })

  const { data: buyers = [], isLoading } = useQuery<Buyer[]>({
    queryKey: ['buyers'],
    queryFn: getBuyers,
    retry: 1,
  })

  const createMutation = useMutation({
    mutationFn: createBuyer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buyers'] })
      setShowForm(false)
      setForm({ name: '', gst_number: '', address: '', email: '', phone: '' })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    createMutation.mutate(form)
  }

  return (
    <AppLayout>
      <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Buyers</h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Manage customer / buyer records</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            <Plus size={14} /> Add Buyer
          </button>
        </div>

        {/* Add Buyer Form */}
        {showForm && (
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 24, marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>New Buyer</span>
              <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 16 }}>
                {[
                  { key: 'name', label: 'Name *', placeholder: 'Buyer name' },
                  { key: 'gst_number', label: 'GST Number', placeholder: 'e.g. 27AAAA...' },
                  { key: 'email', label: 'Email', placeholder: 'contact@example.com' },
                  { key: 'phone', label: 'Phone', placeholder: '+91 9876543210' },
                ].map(({ key, label, placeholder }) => (
                  <div key={key}>
                    <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>{label}</label>
                    <input
                      type="text"
                      placeholder={placeholder}
                      value={(form as any)[key]}
                      onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                      style={{ width: '100%', padding: '8px 10px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Address</label>
                <textarea
                  placeholder="Full address"
                  value={form.address || ''}
                  onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                  rows={2}
                  style={{ width: '100%', padding: '8px 10px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13, outline: 'none', resize: 'vertical', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  style={{ padding: '8px 18px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: createMutation.isPending ? 0.7 : 1 }}
                >
                  {createMutation.isPending ? 'Saving…' : 'Save Buyer'}
                </button>
                <button type="button" onClick={() => setShowForm(false)} style={{ padding: '8px 18px', background: 'var(--bg-surface)', color: 'var(--text-secondary)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}>
                  Cancel
                </button>
              </div>
              {createMutation.isError && (
                <p style={{ marginTop: 8, fontSize: 12, color: 'var(--error)' }}>Error: {(createMutation.error as Error).message}</p>
              )}
            </form>
          </div>
        )}

        {/* Buyers list */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          {isLoading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
          ) : buyers.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center' }}>
              <Users size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px', display: 'block' }} />
              <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No buyers yet</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Add your first buyer to get started.</p>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}>
                  {['Name', 'GST Number', 'Contact', 'Address'].map((h) => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {buyers.map((buyer) => (
                  <tr
                    key={buyer.id}
                    style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.1s' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '11px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 28, height: 28, borderRadius: 6, background: 'var(--accent-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Users size={13} color="var(--accent)" />
                        </div>
                        {buyer.name}
                      </div>
                    </td>
                    <td style={{ padding: '11px 16px', color: buyer.gst_number ? 'var(--text-primary)' : 'var(--text-muted)', fontFamily: buyer.gst_number ? 'monospace' : 'inherit', fontSize: buyer.gst_number ? 12 : 13 }}>
                      {buyer.gst_number ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><Hash size={11} />{buyer.gst_number}</span>
                      ) : '—'}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {buyer.email && <span style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 5 }}><Mail size={11} />{buyer.email}</span>}
                        {buyer.phone && <span style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 5 }}><Phone size={11} />{buyer.phone}</span>}
                        {!buyer.email && !buyer.phone && <span style={{ color: 'var(--text-muted)' }}>—</span>}
                      </div>
                    </td>
                    <td style={{ padding: '11px 16px', color: 'var(--text-secondary)', fontSize: 12 }}>
                      {buyer.address ? (
                        <span style={{ display: 'flex', alignItems: 'flex-start', gap: 5 }}><MapPin size={11} style={{ flexShrink: 0, marginTop: 2 }} />{buyer.address}</span>
                      ) : '—'}
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
