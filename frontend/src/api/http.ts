import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'

export type ApiEnvelope<T> = {
  success: boolean
  code: number
  message: string
  data: T
}

function unwrap<T>(payload: ApiEnvelope<T>): T {
  if (!payload.success) {
    const msg = payload.message || `错误码 ${payload.code}`
    throw new Error(msg)
  }
  return payload.data
}

export const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err?.response?.data?.message || err.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(err)
  },
)

export async function getData<T>(url: string, config?: object): Promise<T> {
  const res = await http.get<ApiEnvelope<T>>(url, config)
  return unwrap(res.data)
}

export async function postData<T>(url: string, body?: unknown): Promise<T> {
  const res = await http.post<ApiEnvelope<T>>(url, body)
  return unwrap(res.data)
}

/** 业务失败但 HTTP 200（如 publish 校验失败） */
export async function postEnvelope<T>(url: string, body?: unknown): Promise<ApiEnvelope<T>> {
  const res = await http.post<ApiEnvelope<T>>(url, body)
  return res.data
}
