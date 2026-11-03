import type { Metadata } from 'next';
import { ThemeProvider } from 'next-themes';
import { Toaster } from 'react-hot-toast';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import './globals.css';

export const metadata: Metadata = {
  title: 'Roadies | 10-Year Geospatial Road Infrastructure Analytics (2016–2026)',
  description:
    'Academic geospatial analytics platform for road infrastructure change detection in India. Empirical OpenStreetMap network history, Sentinel-2 & Landsat remote sensing, and urban sprawl analysis (2016–2026).',
  keywords: [
    'Roadies',
    'road infrastructure analysis',
    'OSM ohsome',
    'India roads',
    'geospatial analytics',
    'change detection',
    'urban expansion',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-slate-950 text-slate-100 antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange={false}
        >
          <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <Sidebar />

            {/* Main content */}
            <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
              <Navbar />
              <main className="flex-1 overflow-y-auto">
                {children}
              </main>
            </div>
          </div>

          {/* Toast notifications */}
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: '#1e293b',
                color: '#f1f5f9',
                border: '1px solid #334155',
                borderRadius: '10px',
                fontSize: '13px',
              },
              success: {
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#1e293b',
                },
              },
              error: {
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#1e293b',
                },
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
