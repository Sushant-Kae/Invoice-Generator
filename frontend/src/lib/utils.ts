export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ')
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(value)
}

export function formatNumber(value: number, decimals = 2): string {
  return value.toFixed(decimals)
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 80) return '#16a34a'
  if (confidence >= 50) return '#d97706'
  return '#dc2626'
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 80) return 'High'
  if (confidence >= 50) return 'Medium'
  return 'Low'
}
