export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

let onUnauthorizedCallback: (() => void) | null = null

export function setOnUnauthorized(callback: (() => void) | null) {
  onUnauthorizedCallback = callback
}

export async function apiClient<T>(
  url: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, headers, ...rest } = options

  const reqHeaders = new Headers(headers)
  let reqBody: BodyInit | null | undefined = undefined

  if (body !== undefined && body !== null) {
    if (typeof body === 'string' || body instanceof FormData || body instanceof URLSearchParams) {
      reqBody = body
    } else {
      if (!reqHeaders.has('Content-Type')) {
        reqHeaders.set('Content-Type', 'application/json')
      }
      reqBody = JSON.stringify(body)
    }
  }

  const response = await fetch(url, {
    credentials: 'include',
    headers: reqHeaders,
    body: reqBody,
    ...rest,
  })

  let responseData: unknown = null
  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    try {
      responseData = await response.json()
    } catch {
      responseData = null
    }
  } else {
    try {
      responseData = await response.text()
    } catch {
      responseData = null
    }
  }

  if (!response.ok) {
    let detail = 'Произошла ошибка при выполнении запроса'

    if (responseData && typeof responseData === 'object') {
      const dataObj = responseData as Record<string, unknown>
      if (typeof dataObj.detail === 'string') {
        detail = dataObj.detail
      } else if (Array.isArray(dataObj.detail)) {
        detail = dataObj.detail
          .map((item) => {
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: unknown }).msg)
            }
            return String(item)
          })
          .join(', ')
      }
    } else if (typeof responseData === 'string' && responseData.trim()) {
      detail = responseData
    }

    if (response.status === 401) {
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        try {
          onUnauthorizedCallback?.()
        } catch {
          // ignore error in callback
        }
        window.location.href = '/login'
      }
    }

    throw new ApiError(response.status, detail)
  }

  return responseData as T
}
