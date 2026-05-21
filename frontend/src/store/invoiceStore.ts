import { create } from 'zustand'
import type { ExtractedItem, InvoiceCreate } from '@/lib/api'

export type WizardStep = 'upload' | 'review' | 'preview' | 'done'

export interface InvoiceItem extends ExtractedItem {
  sr_no: number
  estimated_profit: number
}

interface InvoiceStore {
  // Wizard state
  step: WizardStep
  setStep: (s: WizardStep) => void

  // Upload state
  uploadedFileId: string | null
  uploadedFilename: string | null
  setUploadedFile: (fileId: string, filename: string) => void

  // Extraction state
  extractedItems: InvoiceItem[]
  extractionMethod: string | null
  extractionConfidence: number
  extractionWarnings: string[]
  setExtractionResult: (
    items: InvoiceItem[],
    method: string,
    confidence: number,
    warnings: string[]
  ) => void

  // Invoice form state
  invoiceNumber: string
  invoiceDate: string
  buyerName: string
  buyerGst: string
  taxMode: 'cgst_sgst' | 'igst' | 'none'
  cgstPercent: number
  sgstPercent: number
  igstPercent: number
  globalMargin: number

  setInvoiceField: <K extends keyof InvoiceStore>(
    field: K,
    value: InvoiceStore[K]
  ) => void

  // Item editing
  updateItem: (index: number, field: keyof InvoiceItem, value: string | number) => void
  applyGlobalMargin: () => void

  // Generated invoice
  generatedInvoiceId: number | null
  docxUrl: string | null
  pdfUrl: string | null
  setGeneratedResult: (invoiceId: number, docxUrl?: string, pdfUrl?: string) => void

  // Computed totals
  getSubtotal: () => number
  getTaxAmount: () => number
  getTotalAmount: () => number

  // Reset
  reset: () => void
}

const recalcItem = (item: InvoiceItem, margin: number): InvoiceItem => {
  const sellingRate = item.purchase_rate * (1 + margin / 100)
  const amount = parseFloat((sellingRate * item.qty).toFixed(2))
  const estimatedProfit = parseFloat((amount - item.purchase_rate * item.qty).toFixed(2))
  return {
    ...item,
    margin_percent: margin,
    selling_rate: parseFloat(sellingRate.toFixed(2)),
    amount,
    estimated_profit: estimatedProfit,
  }
}

const today = () => new Date().toISOString().split('T')[0]

const initialState = {
  step: 'upload' as WizardStep,
  uploadedFileId: null,
  uploadedFilename: null,
  extractedItems: [],
  extractionMethod: null,
  extractionConfidence: 0,
  extractionWarnings: [],
  invoiceNumber: `INV-${new Date().getFullYear()}-${String(Date.now()).slice(-4)}`,
  invoiceDate: today(),
  buyerName: '',
  buyerGst: '',
  taxMode: 'igst' as const,
  cgstPercent: 9,
  sgstPercent: 9,
  igstPercent: 18,
  globalMargin: 10,
  generatedInvoiceId: null,
  docxUrl: null,
  pdfUrl: null,
}

export const useInvoiceStore = create<InvoiceStore>((set, get) => ({
  ...initialState,

  setStep: (step) => set({ step }),

  setUploadedFile: (fileId, filename) =>
    set({ uploadedFileId: fileId, uploadedFilename: filename }),

  setExtractionResult: (items, method, confidence, warnings) =>
    set({
      extractedItems: items.map((item, i) => ({
        ...item,
        sr_no: i + 1,
        estimated_profit:
          (item.selling_rate - item.purchase_rate) * item.qty,
      })),
      extractionMethod: method,
      extractionConfidence: confidence,
      extractionWarnings: warnings,
    }),

  setInvoiceField: (field, value) => set({ [field]: value } as any),

  updateItem: (index, field, value) =>
    set((state) => {
      const items = [...state.extractedItems]
      const item = { ...items[index], [field]: value }

      // Auto-recalculate selling_rate and amount when purchase_rate, margin, or qty changes
      if (field === 'purchase_rate' || field === 'margin_percent' || field === 'qty') {
        const rate = field === 'purchase_rate' ? Number(value) : item.purchase_rate
        const margin = field === 'margin_percent' ? Number(value) : item.margin_percent
        const qty = field === 'qty' ? Number(value) : item.qty
        const sellingRate = parseFloat((rate * (1 + margin / 100)).toFixed(2))
        item.selling_rate = sellingRate
        item.amount = parseFloat((sellingRate * qty).toFixed(2))
        item.estimated_profit = parseFloat(((sellingRate - rate) * qty).toFixed(2))
      }

      items[index] = item
      return { extractedItems: items }
    }),

  applyGlobalMargin: () =>
    set((state) => ({
      extractedItems: state.extractedItems.map((item) =>
        recalcItem(item, state.globalMargin)
      ),
    })),

  setGeneratedResult: (invoiceId, docxUrl, pdfUrl) =>
    set({ generatedInvoiceId: invoiceId, docxUrl: docxUrl ?? null, pdfUrl: pdfUrl ?? null }),

  getSubtotal: () =>
    get().extractedItems.reduce((sum, item) => sum + item.amount, 0),

  getTaxAmount: () => {
    const s = get()
    const sub = s.getSubtotal()
    if (s.taxMode === 'cgst_sgst')
      return (sub * (s.cgstPercent + s.sgstPercent)) / 100
    if (s.taxMode === 'igst') return (sub * s.igstPercent) / 100
    return 0
  },

  getTotalAmount: () => get().getSubtotal() + get().getTaxAmount(),

  reset: () => set({ ...initialState, invoiceNumber: `INV-${new Date().getFullYear()}-${String(Date.now()).slice(-4)}`, invoiceDate: today() }),
}))
