import api from './request'

// 媒体工具能力（公开）
export function getCapabilities() {
  return api.get('/media-tools/capabilities')
}

// 上传并探测媒体文件（multipart/form-data）
export function uploadMediaFile(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/media-tools/files', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
    // 后端上限 500MB，慢网下 120s 必超时
    timeout: 300000
  })
}

// 查询媒体文件元数据
export function getMediaFile(id) {
  return api.get(`/media-tools/files/${id}`)
}

// 删除媒体文件（软删除）
export function deleteMediaFile(id) {
  return api.delete(`/media-tools/files/${id}`)
}

// 查询用户文件列表
export function listMediaFiles(params) {
  return api.get('/media-tools/files', { params })
}

// 创建转换/压缩/截取/提取音频/音频转换任务
export function createConvertTask(data) {
  return api.post('/media-tools/tasks/convert', data)
}

export function createGifTask(data) {
  return api.post('/media-tools/tasks/gif', data)
}

export function createMergeTask(data) {
  return api.post('/media-tools/tasks/merge', data)
}

export function createWatermarkTask(data) {
  return api.post('/media-tools/tasks/watermark', data)
}

export function createRedactTask(data) {
  return api.post('/media-tools/tasks/redact', data)
}

// 查询任务状态
export function getMediaTask(id) {
  return api.get(`/media-tools/tasks/${id}`)
}

export function cancelMediaTask(id) {
  return api.post(`/media-tools/tasks/${id}/cancel`)
}

export function deleteMediaTask(id) {
  return api.delete(`/media-tools/tasks/${id}`)
}

export function deleteMediaTasks(taskIds) {
  return api.post('/media-tools/tasks/delete-batch', { task_ids: taskIds })
}

// 重试失败任务
export function retryMediaTask(id) {
  return api.post(`/media-tools/tasks/${id}/retry`)
}

// 批量重试失败任务
export function retryMediaTasks(taskIds) {
  return api.post('/media-tools/tasks/retry-batch', { task_ids: taskIds })
}

// 获取任务输出下载地址
export function getMediaTaskDownload(id) {
  return api.get(`/media-tools/tasks/${id}/download`)
}

// 查询任务历史
export function listMediaTasks(params) {
  return api.get('/media-tools/tasks', { params })
}
