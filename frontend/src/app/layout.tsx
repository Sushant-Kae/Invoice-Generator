import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
    title: 'Shah Enterprises Invoice Generator',
    description: 'Invoice Generator System',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    )
}