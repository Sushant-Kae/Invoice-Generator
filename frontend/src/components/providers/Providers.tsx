'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { Toaster } from 'react-hot-toast'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 30_000 },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1c2333',
            color: '#e6edf3',
            border: '1px solid #30363d',
            borderRadius: '8px',
            fontSize: '14px',
          },
          success: { iconTheme: { primary: '#16a34a', secondary: '#1c2333' } },
          error:   { iconTheme: { primary: '#dc2626', secondary: '#1c2333' } },
        }}
      />
    </QueryClientProvider>
  )
}
