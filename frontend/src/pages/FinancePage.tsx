import React from 'react'
import { Card } from '../components/ui'

export const FinancePage: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col gap-4">
      <Card>
        <h2 className="text-2xl font-heading font-semibold text-text mb-2">Учёт</h2>
        <p className="text-muted text-base">Скоро</p>
      </Card>
    </div>
  )
}
