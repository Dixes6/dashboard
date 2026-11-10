import React, { useState, useEffect, useMemo } from 'react'
import { Search, Phone, MessageCircle, Users, X } from 'lucide-react'
import {
  useInfiniteClients,
  useClientsTotalCount,
  useCreateClient,
  useUpdateClient,
  useDeleteClient,
} from '../api'
import type { ClientResponse } from '../api'
import { ApiError } from '../api/client'
import { Button, Input, Card, Spinner, EmptyState, BottomSheet, useToast } from '../components/ui'
import { formatMoney, formatPhone } from '../lib'

export const ClientsPage: React.FC = () => {
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // 300ms debounce for search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim())
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Determine whether search query is phone-like or name-like
  const { qParam, phoneParam } = useMemo(() => {
    if (!debouncedSearch) {
      return { qParam: undefined, phoneParam: undefined }
    }
    // If only digits, +, spaces, (), -
    const isPhoneLike = /^[0-9+\s()-]+$/.test(debouncedSearch)
    if (isPhoneLike) {
      const digitsOnly = debouncedSearch.replace(/\D/g, '')
      return { qParam: undefined, phoneParam: digitsOnly || undefined }
    }
    return { qParam: debouncedSearch, phoneParam: undefined }
  }, [debouncedSearch])

  // Total count of clients without filters
  const { data: totalClientsCount = 0 } = useClientsTotalCount()

  // Paginated client list (30 per page)
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useInfiniteClients({
    q: qParam,
    phone: phoneParam,
    limit: 30,
  })

  const clients = useMemo(() => {
    if (!data?.pages) return []
    return data.pages.flatMap((page) => page.items)
  }, [data])

  const totalFilteredCount = data?.pages?.[0]?.total ?? 0

  const createClientMutation = useCreateClient()
  const updateClientMutation = useUpdateClient()
  const deleteClientMutation = useDeleteClient()
  const { showToast } = useToast()

  // BottomSheet modal state
  const [isSheetOpen, setSheetOpen] = useState(false)
  const [editingClient, setEditingClient] = useState<ClientResponse | null>(null)

  // Form states
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [notes, setNotes] = useState('')

  // Form errors
  const [nameError, setNameError] = useState<string | null>(null)
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [generalError, setGeneralError] = useState<string | null>(null)

  // Confirmation dialog state for deletion
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)

  const handleOpenCreate = () => {
    setEditingClient(null)
    setName('')
    setPhone('')
    setNotes('')
    setNameError(null)
    setPhoneError(null)
    setGeneralError(null)
    setIsConfirmingDelete(false)
    setSheetOpen(true)
  }

  const handleOpenEdit = (client: ClientResponse) => {
    setEditingClient(client)
    setName(client.name)
    setPhone(formatPhone(client.phone))
    setNotes(client.notes || '')
    setNameError(null)
    setPhoneError(null)
    setGeneralError(null)
    setIsConfirmingDelete(false)
    setSheetOpen(true)
  }

  const handleCloseSheet = () => {
    setSheetOpen(false)
    setIsConfirmingDelete(false)
  }

  const validateForm = (): boolean => {
    let isValid = true
    setNameError(null)
    setPhoneError(null)
    setGeneralError(null)

    const trimmedName = name.trim()
    if (!trimmedName) {
      setNameError('Имя клиента не может быть пустым')
      isValid = false
    } else if (trimmedName.length > 200) {
      setNameError('Имя не должно превышать 200 символов')
      isValid = false
    }

    const trimmedPhone = phone.trim()
    if (!trimmedPhone) {
      setPhoneError('Номер телефона не может быть пустым')
      isValid = false
    }

    return isValid
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    const trimmedName = name.trim()
    const rawPhone = phone.trim()
    const trimmedNotes = notes.trim() ? notes.trim() : null

    try {
      if (editingClient) {
        await updateClientMutation.mutateAsync({
          id: editingClient.id,
          payload: {
            name: trimmedName,
            phone: rawPhone,
            notes: trimmedNotes,
          },
        })
        showToast('Данные клиента обновлены', 'success')
      } else {
        await createClientMutation.mutateAsync({
          name: trimmedName,
          phone: rawPhone,
          notes: trimmedNotes,
        })
        showToast('Клиент успешно добавлен', 'success')
      }
      handleCloseSheet()
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setPhoneError(err.detail)
          showToast(err.detail, 'danger')
        } else if (err.status === 422) {
          const message = 'Проверьте номер телефона'
          setPhoneError(message)
          showToast(message, 'danger')
        } else {
          setGeneralError(err.detail)
          showToast(err.detail, 'danger')
        }
      } else {
        const fallback = 'Произошла непредвиденная ошибка'
        setGeneralError(fallback)
        showToast(fallback, 'danger')
      }
    }
  }

  const handleDelete = async () => {
    if (!editingClient) return
    try {
      await deleteClientMutation.mutateAsync(editingClient.id)
      showToast('Клиент успешно удалён', 'info')
      handleCloseSheet()
    } catch (err) {
      let message = 'Не удалось удалить клиента'
      if (err instanceof ApiError) {
        message = err.detail
      }
      showToast(message, 'danger')
    }
  }

  const isSubmitting =
    createClientMutation.isPending ||
    updateClientMutation.isPending ||
    deleteClientMutation.isPending

  const editingPhoneDigits = editingClient ? editingClient.phone.replace(/\D/g, '') : ''

  return (
    <div className="flex-1 flex flex-col gap-4 pb-6 font-sans">
      {/* Top Header Block */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-2xl font-heading font-semibold text-text">Клиенты</h2>
          <span className="text-xs text-muted font-medium">
            Клиентов всего: {totalClientsCount}
          </span>
        </div>

        <Button
          variant="primary"
          onClick={handleOpenCreate}
          className="min-h-[44px] h-11 px-3.5 sm:px-4 text-sm whitespace-nowrap"
        >
          <span>Добавить клиента</span>
        </Button>
      </div>

      {/* Search Input with Debounce */}
      <div className="relative">
        <Input
          type="text"
          placeholder="Имя или телефон"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pr-10"
        />
        {searchInput ? (
          <button
            type="button"
            onClick={() => setSearchInput('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center text-muted hover:text-text cursor-pointer rounded-full"
            aria-label="Очистить поиск"
          >
            <X className="w-4 h-4" />
          </button>
        ) : (
          <div className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none">
            <Search className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Content states */}
      {isLoading ? (
        <div className="flex-1 flex flex-col items-center justify-center py-16">
          <Spinner size="lg" />
          <span className="text-sm text-muted mt-3">Загрузка клиентов...</span>
        </div>
      ) : isError ? (
        <div className="flex-1 flex flex-col justify-center items-center py-12">
          <Card className="w-full text-center p-6 flex flex-col items-center gap-3">
            <p className="text-danger font-medium">
              {error instanceof ApiError ? error.detail : 'Не удалось загрузить список клиентов'}
            </p>
            <Button variant="secondary" onClick={() => refetch()} className="min-h-[44px]">
              Повторить
            </Button>
          </Card>
        </div>
      ) : clients.length === 0 ? (
        debouncedSearch ? (
          <EmptyState
            icon={<Search className="w-10 h-10" />}
            title="Ничего не найдено"
            description={`По запросу «${debouncedSearch}» совпадений нет. Проверьте правильность ввода.`}
            action={
              <Button
                variant="secondary"
                onClick={() => setSearchInput('')}
                className="min-h-[44px] mt-2"
              >
                Сбросить поиск
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={<Users className="w-10 h-10" />}
            title="Пока нет клиентов"
            description="Добавьте первого клиента, чтобы вести историю посещений и учитывать выручку."
            action={
              <Button variant="primary" onClick={handleOpenCreate} className="min-h-[44px] mt-2">
                Добавить клиента
              </Button>
            }
          />
        )
      ) : (
        <div className="flex flex-col gap-2.5" role="list" aria-label="Список клиентов">
          {clients.map((client) => {
            const digitsOnly = client.phone.replace(/\D/g, '')
            const waUrl = `https://wa.me/${digitsOnly}`
            const telUrl = `tel:+${digitsOnly}`

            return (
              <div
                key={client.id}
                role="listitem"
                onClick={() => handleOpenEdit(client)}
                className="bg-surface border border-border rounded-card p-3.5 sm:p-4 shadow-soft hover:border-primary/40 transition-colors duration-150 cursor-pointer flex items-center justify-between gap-3 select-none"
              >
                {/* Left: Client info */}
                <div className="flex-1 min-w-0 pr-1">
                  <h3 className="text-base font-semibold text-text truncate">
                    {client.name}
                  </h3>
                  <div className="text-xs text-muted mt-0.5 font-medium">
                    {formatPhone(client.phone)}
                  </div>
                  <div className="text-xs text-muted/80 mt-1.5 flex items-center gap-2 flex-wrap">
                    <span>Визитов: {client.visits_count}</span>
                    <span className="text-border">•</span>
                    <span className="font-semibold text-text">
                      {formatMoney(client.total_earned)}
                    </span>
                  </div>
                </div>

                {/* Right: Quick actions (WhatsApp, Phone) >= 44px */}
                <div
                  className="flex items-center gap-1 shrink-0"
                  onClick={(e) => e.stopPropagation()}
                >
                  <a
                    href={waUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Написать ${client.name} в WhatsApp`}
                    className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-btn flex items-center justify-center text-success hover:bg-success/10 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                  >
                    <MessageCircle className="w-5 h-5" />
                  </a>

                  <a
                    href={telUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Позвонить ${client.name}`}
                    className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-btn flex items-center justify-center text-primary hover:bg-primary-soft transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    <Phone className="w-5 h-5" />
                  </a>
                </div>
              </div>
            )
          })}

          {/* Pagination: "Показать ещё" button */}
          {hasNextPage && (
            <div className="pt-3 flex justify-center">
              <Button
                variant="secondary"
                onClick={() => fetchNextPage()}
                loading={isFetchingNextPage}
                className="w-full min-h-[48px]"
              >
                Показать ещё
              </Button>
            </div>
          )}

          {/* Count info summary */}
          <div className="text-center text-xs text-muted pt-1">
            Показано {clients.length} из {totalFilteredCount}
          </div>
        </div>
      )}

      {/* BottomSheet for create / edit */}
      <BottomSheet
        isOpen={isSheetOpen}
        onClose={handleCloseSheet}
        title={editingClient ? 'Редактирование клиента' : 'Новый клиент'}
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-1">
          <Input
            label="Имя"
            placeholder="Например, Анна Смирнова"
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              if (nameError) setNameError(null)
            }}
            error={nameError || undefined}
            maxLength={200}
            required
          />

          <Input
            label="Телефон"
            type="tel"
            placeholder="+7 (999) 000-00-00"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value)
              if (phoneError) setPhoneError(null)
            }}
            error={phoneError || undefined}
            required
          />

          {/* Multiline Notes */}
          <div className="w-full flex flex-col gap-1.5">
            <div className="flex justify-between items-center">
              <label htmlFor="client-notes" className="text-sm font-medium text-text">
                Заметка
              </label>
              <span className="text-xs text-muted">{notes.length}/2000</span>
            </div>
            <textarea
              id="client-notes"
              rows={3}
              maxLength={2000}
              placeholder="Особенности, пожелания, аллергии..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full p-3 rounded-btn bg-surface border border-border text-text placeholder:text-muted transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface resize-none text-sm"
            />
          </div>

          {/* Contact quick actions inside edit modal */}
          {editingClient && (
            <div className="flex items-center gap-2 pt-1">
              <a
                href={`https://wa.me/${editingPhoneDigits}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 min-h-[44px] h-11 px-3 rounded-btn border border-success/30 bg-success/10 text-success text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 hover:bg-success/20 transition-colors"
              >
                <MessageCircle className="w-4 h-4 shrink-0" />
                <span>WhatsApp</span>
              </a>

              <a
                href={`tel:+${editingPhoneDigits}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 min-h-[44px] h-11 px-3 rounded-btn border border-primary/30 bg-primary-soft text-primary text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 hover:bg-border/60 transition-colors"
              >
                <Phone className="w-4 h-4 shrink-0" />
                <span>Позвонить</span>
              </a>
            </div>
          )}

          {generalError ? (
            <div
              role="alert"
              className="text-xs text-danger font-medium p-2.5 rounded-btn bg-danger/10 border border-danger/20 text-center"
            >
              {generalError}
            </div>
          ) : null}

          {/* Form action buttons */}
          <div className="flex flex-col gap-2.5 mt-2">
            <Button
              type="submit"
              variant="primary"
              loading={isSubmitting}
              className="w-full"
            >
              Сохранить
            </Button>

            {editingClient && (
              <>
                {!isConfirmingDelete ? (
                  <Button
                    type="button"
                    variant="danger"
                    onClick={() => setIsConfirmingDelete(true)}
                    className="w-full"
                  >
                    Удалить клиента
                  </Button>
                ) : (
                  <div className="p-3 rounded-btn border border-danger/30 bg-danger/5 flex flex-col gap-2.5 animate-in fade-in duration-150">
                    <p className="text-xs text-text text-center font-medium">
                      Удалить клиента «{editingClient.name}»?
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="danger"
                        onClick={handleDelete}
                        loading={isSubmitting}
                        className="flex-1 min-h-[44px] h-11 text-sm"
                      >
                        Да, удалить
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setIsConfirmingDelete(false)}
                        className="flex-1 min-h-[44px] h-11 text-sm"
                      >
                        Отмена
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </form>
      </BottomSheet>
    </div>
  )
}
