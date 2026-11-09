import api from './request'
import { downloadBinary } from './download'

export function startInterview(data) {
  // 出题前还有一次岗位差距分析，DeepSeek 推理模型实测单次 30-40s，
  // 默认 60s 会在服务端返回前先超时，前端只看到「题目生成失败」。
  // 放宽到 120s，与简历上传接口保持一致。
  return api.post('/interviews/start', data, { timeout: 120000 })
}

export async function submitAnswerStream(interviewId, answer, onChunk, onDone) {
  const authStore = (await import('../stores/auth')).useAuthStore()
  const response = await fetch(`/api/v1/interviews/${interviewId}/answer/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authStore.token}`
    },
    body: JSON.stringify({ answer })
  })

  if (!response.ok || !response.body) {
    throw new Error(`请求失败（HTTP ${response.status}）`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  // 标记是否已收到终态事件（done / error）。
  // 若流自然结束却没收到终态，说明连接被中途掐断，调用方需要自愈（重新拉取消息）。
  let settled = false
  let streamError = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        let data
        try {
          data = JSON.parse(line.slice(6))
        } catch (e) {
          // 不完整的 JSON 分片，跳过等待后续数据
          continue
        }
        if (data.type === 'chunk') {
          onChunk(data.content)
        } else if (data.type === 'done') {
          settled = true
          await onDone(data)
        } else if (data.type === 'error') {
          // 后端已明确报错：记录后跳出，交由调用方展示并自愈，
          // 不再 throw（throw 会直接炸断调用方的收尾逻辑，导致光标永久闪烁）。
          settled = true
          streamError = new Error(data.content || '评估服务异常')
        }
      }
    }
  }

  return { settled, error: streamError }
}

export function getReport(interviewId) {
  return api.get(`/interviews/${interviewId}/report`)
}

export function getGapAnalysis(interviewId) {
  return api.get(`/interviews/${interviewId}/gap-analysis`)
}

// 报告由后台生成：生成失败或长时间未就绪时，用户可主动要求重新生成。
// 后端带 30 秒节流，重复点击不会造成任务风暴。
export function regenerateReport(interviewId) {
  return api.post(`/interviews/${interviewId}/report/regenerate`)
}

export function exportReportDocx(interviewId) {
  return downloadBinary(`/api/v1/interviews/${interviewId}/report/export-docx`, `interview_${interviewId}_report.docx`)
}

export function getMessages(interviewId) {
  return api.get(`/interviews/${interviewId}/messages`)
}

export function getInterviews() {
  return api.get('/interviews')
}

export function deleteInterview(interviewId) {
  return api.delete(`/interviews/${interviewId}`)
}

export function getAnalysis() {
  return api.get('/interviews/analysis')
}

export function startPractice(experienceId, questionCount = 5) {
  return api.post(`/experiences/${experienceId}/practice`, { question_count: questionCount })
}

export function shareInterview(interviewId) {
  return api.post(`/interviews/${interviewId}/share`)
}

export function unshareInterview(interviewId) {
  return api.delete(`/interviews/${interviewId}/share`)
}

export function getSharedReport(shareToken) {
  return api.get(`/shared/${shareToken}`)
}
