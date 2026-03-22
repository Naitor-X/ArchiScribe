import { Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <a href="/" className="text-xl font-bold text-gray-900">
            ArchiScribe
          </a>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}
