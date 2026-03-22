import { NavLink } from 'react-router-dom'

interface NavItem {
  to: string
  label: string
}

const navItems: NavItem[] = [
  { to: '/inbox', label: 'Inbox' },
  { to: '/projekte', label: 'Projekte' },
  { to: '/archiv', label: 'Archiv' },
  { to: '/einstellungen', label: 'Einstellungen' },
]

export default function Sidebar() {
  return (
    <aside className="w-[200px] bg-gray-100 border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Header mit Logo */}
      <div className="p-4 border-b border-gray-200">
        <NavLink to="/" className="block">
          <span className="text-xl font-bold text-gray-900">Archi</span>
          <span className="text-xl font-light text-gray-600">Scribe</span>
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-white text-gray-900 font-medium shadow-sm'
                      : 'text-gray-600 hover:bg-gray-200 hover:text-gray-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 text-xs text-gray-400">
        v1.0.0
      </div>
    </aside>
  )
}
