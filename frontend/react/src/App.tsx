import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import Inbox from '@/pages/Inbox'
import Projekte from '@/pages/Projekte'
import Archiv from '@/pages/Archiv'
import Einstellungen from '@/pages/Einstellungen'
import ProjectDetail from '@/pages/ProjectDetail'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 Sekunden
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            {/* Redirect root to inbox */}
            <Route index element={<Navigate to="/inbox" replace />} />

            {/* Inbox - Neue Projekte (needs_review) */}
            <Route path="inbox" element={<Inbox />} />
            <Route path="inbox/:id" element={<ProjectDetail />} />

            {/* Projekte - Aktive Projekte (aktiv) */}
            <Route path="projekte" element={<Projekte />} />
            <Route path="projekte/:id" element={<ProjectDetail />} />

            {/* Archiv - Platzhalter */}
            <Route path="archiv" element={<Archiv />} />

            {/* Einstellungen - Platzhalter */}
            <Route path="einstellungen" element={<Einstellungen />} />

            {/* Legacy routes redirect */}
            <Route path="projects/:id" element={<ProjectDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
