/**
 * Health check composable
 *
 * Demonstrates usage of TypeScript types from ~/types/api
 */
import type { HealthCheckResponse, ApiError } from '~/types/api'

export const useHealthCheck = () => {
  const config = useRuntimeConfig()
  const { data, error, pending, refresh } = useFetch<HealthCheckResponse>(
    `${config.public.apiBase}/api/health`,
    {
      method: 'GET',
    }
  )

  return {
    healthData: data,
    healthError: error,
    isLoading: pending,
    refreshHealth: refresh,
  }
}
