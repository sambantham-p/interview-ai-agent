import { useMutation } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { toErrorMessage } from '../../lib/errorMessage'
import { useToast } from '../../lib/toastContext'

export function useReportPdfDownload(sessionId: string | undefined) {
  const { showToast } = useToast()

  return useMutation({
    mutationFn: async () => {
      const pdf = await api.postForBlob(`/interview/${sessionId}/report/pdf`, {})
      const url = URL.createObjectURL(pdf)
      const link = document.createElement('a')
      link.href = url
      link.download = `interview-report-${sessionId}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    },
    onError: (error) => showToast(toErrorMessage(error, 'Could not download the PDF.'), 'error'),
  })
}
