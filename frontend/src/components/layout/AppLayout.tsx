import React, { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Menu, Bell, X, Calendar, Wallet, Users, Sparkles, LogOut } from 'lucide-react'
import { useAuth } from '../../api'
import { useToast } from '../ui'

const NAV_ITEMS = [
  { to: '/', label: 'Главная', icon: Calendar, exact: true },
  { to: '/finance', label: 'Учёт', icon: Wallet },
  { to: '/clients', label: 'Клиенты', icon: Users },
  { to: '/services', label: 'Услуги', icon: Sparkles },
]

export const AppLayout: React.FC = () => {
  const [isMenuOpen, setMenuOpen] = useState(false)
  const { logout } = useAuth()
  const { showToast } = useToast()
  const location = useLocation()

  const currentItem = NAV_ITEMS.find((item) =>
    item.exact ? location.pathname === item.to : location.pathname.startsWith(item.to),
  )
  const pageTitle = currentItem ? currentItem.label : 'Dashboard'

  const handleNavClick = () => {
    setMenuOpen(false)
  }

  const handleLogout = async () => {
    setMenuOpen(false)
    await logout()
  }

  return (
    <div className="min-h-[100dvh] max-w-[480px] mx-auto flex flex-col overflow-x-hidden bg-bg text-text pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)] font-sans">
      {/* Sticky Header */}
      <header className="sticky top-0 z-30 bg-surface/90 backdrop-blur-md border-b border-border h-14 min-h-[56px] px-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center text-text hover:text-primary transition-colors cursor-pointer rounded-btn focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Открыть меню навигации"
        >
          <Menu className="w-6 h-6" />
        </button>

        <h1 className="text-2xl font-heading font-semibold text-text tracking-wide select-none">
          {pageTitle}
        </h1>

        <button
          type="button"
          onClick={() => showToast('Скоро')}
          className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center text-muted hover:text-text transition-colors cursor-pointer rounded-btn focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Уведомления"
        >
          <Bell className="w-5 h-5" />
        </button>
      </header>

      {/* Slide-out Menu Drawer */}
      {isMenuOpen ? (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-text/40 transition-opacity duration-150 cursor-pointer"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer Content */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Главное меню"
            className="relative z-10 w-72 max-w-[80vw] h-full bg-surface shadow-2xl flex flex-col justify-between pt-[calc(1rem+env(safe-area-inset-top))] pb-[calc(1.5rem+env(safe-area-inset-bottom))] px-4 transition-transform duration-200"
          >
            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-2xl font-heading font-semibold text-text">
                  Dashboard
                </span>
                <button
                  type="button"
                  onClick={() => setMenuOpen(false)}
                  className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center text-muted hover:text-text rounded-btn cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  aria-label="Закрыть меню"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Navigation links */}
              <nav className="flex flex-col gap-1.5" aria-label="Разделы приложения">
                {NAV_ITEMS.map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.exact}
                      onClick={handleNavClick}
                      className={({ isActive }) =>
                        `min-h-[48px] px-3.5 py-2.5 rounded-btn flex items-center gap-3 transition-colors duration-150 select-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                          isActive
                            ? 'bg-primary-soft text-primary font-semibold'
                            : 'text-text hover:bg-border/40 font-medium'
                        }`
                      }
                    >
                      <Icon className="w-5 h-5 shrink-0" />
                      <span className="text-base">{item.label}</span>
                    </NavLink>
                  )
                })}
              </nav>
            </div>

            {/* Bottom logout action */}
            <div className="pt-4 border-t border-border">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full min-h-[48px] px-3.5 py-2.5 rounded-btn flex items-center gap-3 text-danger hover:bg-danger/10 transition-colors duration-150 font-medium cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger"
              >
                <LogOut className="w-5 h-5 shrink-0" />
                <span className="text-base">Выйти</span>
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Main page content */}
      <main className="flex-1 p-4 flex flex-col">
        <Outlet />
      </main>
    </div>
  )
}
