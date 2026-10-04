/**
 * HTML 转义工具。
 *
 * 用途：任何要交给 `v-html` 渲染的「非可信文本」（AI 输出、用户输入、后台公告等）
 * 都必须先经过这里转义，再拼接自定义标记（如把换行替换为 <br>）。
 *
 * 为什么需要单独抽出来：项目里曾有多处各自手写渲染函数，其中一部分做了转义、
 * 一部分漏了（面试页的 AI 输出就是漏的那一处），散落的实现很难保证一致性。
 */
export function escapeHtml(text) {
  if (text == null) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
