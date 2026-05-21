import { Sidebar } from './Sidebar'

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          minHeight: '100vh',
          background: 'var(--bg-primary)',
          overflow: 'auto',
        }}
      >
        {children}
      </main>
    </div>
  )
}
