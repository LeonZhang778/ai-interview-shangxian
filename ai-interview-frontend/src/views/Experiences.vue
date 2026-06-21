<template>
  <div class="experiences-page">
    <!-- 顶部 Hero -->
    <div class="hero-section">
      <h1>面经广场</h1>
      <p class="hero-desc">汇集各公司各岗位真实面试经验，助你备战每一场面试</p>
    </div>

    <div class="main-container">
      <!-- 筛选区 -->
      <div class="filter-section">
        <div class="filter-row">
          <div class="filter-group">
            <label>公司</label>
            <div class="filter-tags">
              <span
                v-for="c in filterOptions.companies"
                :key="c"
                class="filter-tag"
                :class="{ active: filters.company === c }"
                @click="toggleFilter('company', c)"
              >{{ c }}</span>
            </div>
          </div>
        </div>
        <div class="filter-row">
          <div class="filter-group">
            <label>岗位</label>
            <div class="filter-tags">
              <span
                v-for="p in filterOptions.positions"
                :key="p"
                class="filter-tag"
                :class="{ active: filters.position === p }"
                @click="toggleFilter('position', p)"
              >{{ p }}</span>
            </div>
          </div>
        </div>
        <div class="filter-row filter-row-small">
          <div class="filter-group">
            <label>级别</label>
            <div class="filter-tags">
              <span
                class="filter-tag"
                :class="{ active: !filters.level }"
                @click="filters.level = ''"
              >全部</span>
              <span
                v-for="l in filterOptions.levels"
                :key="l"
                class="filter-tag"
                :class="{ active: filters.level === l }"
                @click="toggleFilter('level', l)"
              >{{ l }}</span>
            </div>
          </div>
          <div class="filter-group">
            <label>轮次</label>
            <div class="filter-tags">
              <span
                class="filter-tag"
                :class="{ active: !filters.round }"
                @click="filters.round = ''"
              >全部</span>
              <span
                v-for="r in filterOptions.rounds"
                :key="r"
                class="filter-tag"
                :class="{ active: filters.round === r }"
                @click="toggleFilter('round', r)"
              >{{ r }}</span>
            </div>
          </div>
        </div>
        <div class="filter-row sort-row">
          <div class="sort-tabs">
            <span
              v-for="s in sortOptions"
              :key="s.value"
              class="sort-tab"
              :class="{ active: filters.sort === s.value }"
              @click="filters.sort = s.value"
            >{{ s.label }}</span>
          </div>
        </div>
      </div>

      <!-- 列表区 -->
      <div class="list-section">
        <div v-if="loading && experiences.length === 0" class="loading-state">
          加载中...
        </div>
        <div v-else-if="experiences.length === 0" class="empty-state">
          暂无面经内容
        </div>
        <div v-else class="experience-list">
          <div
            v-for="exp in experiences"
            :key="exp.id"
            class="experience-card"
            @click="goToDetail(exp.id)"
          >
            <div class="card-header">
              <h3 class="card-title">{{ exp.title }}</h3>
              <div class="card-tags">
                <span class="company-tag">{{ exp.company }}</span>
                <span class="position-tag">{{ exp.position }}</span>
                <span v-if="exp.level" class="level-tag">{{ exp.level }}</span>
                <span v-if="exp.round" class="round-tag">{{ exp.round }}</span>
              </div>
            </div>
            <p class="card-summary" v-if="exp.summary">{{ exp.summary }}</p>
            <div class="card-footer">
              <div class="card-stats">
                <span>阅读 {{ formatCount(exp.view_count) }}</span>
                <span>点赞 {{ formatCount(exp.like_count) }}</span>
                <span>收藏 {{ formatCount(exp.collect_count) }}</span>
              </div>
              <span class="card-date">{{ exp.created_at }}</span>
            </div>
            <div class="card-actions">
              <router-link
                :to="`/experiences/${exp.id}`"
                class="btn-read"
                @click.stop
              >阅读全文</router-link>
              <router-link
                to="/resume/upload"
                class="btn-practice"
                @click.stop
              >用智面模拟这场面试</router-link>
            </div>
          </div>
        </div>

        <!-- 加载更多 -->
        <div v-if="hasMore" class="load-more">
          <button class="btn-load-more" @click="loadMore" :disabled="loading">
            {{ loading ? '加载中...' : '加载更多' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getExperiences, getFilterOptions } from '../api/experience'

const router = useRouter()

const experiences = ref([])
const loading = ref(false)
const hasMore = ref(false)
const currentPage = ref(1)

const filters = reactive({
  company: '',
  position: '',
  level: '',
  round: '',
  sort: 'latest'
})

const filterOptions = reactive({
  companies: [],
  positions: [],
  levels: [],
  rounds: []
})

const sortOptions = [
  { label: '最新发布', value: 'latest' },
  { label: '最多阅读', value: 'popular' },
  { label: '最多收藏', value: 'collected' }
]

function toggleFilter(key, value) {
  filters[key] = filters[key] === value ? '' : value
}

function formatCount(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return n.toString()
}

function goToDetail(id) {
  router.push(`/experiences/${id}`)
}

async function fetchExperiences(reset = false) {
  if (reset) {
    currentPage.value = 1
    experiences.value = []
  }
  loading.value = true
  try {
    const params = { page: currentPage.value, size: 20 }
    if (filters.company) params.company = filters.company
    if (filters.position) params.position = filters.position
    if (filters.level) params.level = filters.level
    if (filters.round) params.round = filters.round
    if (filters.sort) params.sort = filters.sort

    const data = await getExperiences(params)
    if (reset) {
      experiences.value = data.items
    } else {
      experiences.value.push(...data.items)
    }
    hasMore.value = data.has_more
  } catch (e) {
    console.error('加载面经列表失败:', e)
  } finally {
    loading.value = false
  }
}

function loadMore() {
  currentPage.value++
  fetchExperiences(false)
}

async function fetchFilters() {
  try {
    const data = await getFilterOptions()
    filterOptions.companies = data.companies || []
    filterOptions.positions = data.positions || []
    filterOptions.levels = data.levels || []
    filterOptions.rounds = data.rounds || []
  } catch (e) {
    console.error('加载筛选选项失败:', e)
    // 设置默认选项
    filterOptions.companies = ['字节跳动', '腾讯', '阿里巴巴', '美团', '百度', '京东', '快手', '小红书', '华为']
    filterOptions.positions = ['后端开发', '前端开发', '算法工程师', '测试开发', '产品经理']
    filterOptions.levels = ['校招', '1-3年', '3-5年', '5年以上']
    filterOptions.rounds = ['一面', '二面', '三面', 'HR面', '综合']
  }
}

watch(filters, () => {
  fetchExperiences(true)
}, { deep: true })

onMounted(() => {
  fetchFilters()
  fetchExperiences(true)
})
</script>

<style scoped>
.experiences-page {
  min-height: 100vh;
  background: var(--bg-base);
}

.hero-section {
  background: linear-gradient(135deg, rgba(124,58,237,0.2) 0%, rgba(99,102,241,0.15) 50%, rgba(139,92,246,0.1) 100%);
  padding: 48px 20px 40px;
  text-align: center;
  border-bottom: 1px solid var(--border-default);
}

.hero-section h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 32px;
  font-weight: 800;
  margin: 0 0 10px;
  background:var(--title-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-desc {
  font-size: 16px;
  color: var(--text-muted);
  margin: 0;
}

.main-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* 筛选区 */
.filter-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 20px;
}

.filter-row {
  margin-bottom: 14px;
  display: flex;
  gap: 20px;
}
.filter-row:last-child { margin-bottom: 0; }
.filter-row-small { flex-wrap: wrap; }

.filter-group {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.filter-group label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  padding-top: 4px;
  min-width: 36px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-tag {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  background: var(--bg-hover);
  color: var(--text-muted);
  transition: all 0.2s;
  user-select: none;
}
.filter-tag:hover {
  background: rgba(139,92,246,0.12);
  color: var(--accent-purple);
}
.filter-tag.active {
  background: rgba(139,92,246,0.2);
  color: var(--accent-light);
  border: 1px solid rgba(139,92,246,0.3);
}

.sort-row {
  border-top: 1px solid var(--border-default);
  padding-top: 14px;
}
.sort-tabs { display: flex; gap: 0; }
.sort-tab {
  padding: 6px 16px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-muted);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.sort-tab:hover { color: var(--accent-purple); }
.sort-tab.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
  font-weight: 600;
}

/* 列表区 */
.experience-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.experience-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
}
.experience-card:hover {
  border-color: var(--border-hover);
  background: rgba(139,92,246,0.07);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(139,92,246,0.1);
}

.card-header { margin-bottom: 10px; }
.card-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 10px;
  line-height: 1.4;
}

.card-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.company-tag {
  background: rgba(139,92,246,0.1);
  color: var(--accent-purple);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.position-tag {
  background: var(--bg-hover);
  color: var(--accent-purple);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}
.level-tag {
  background: rgba(6,182,212,0.08);
  color: var(--accent-cyan);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}
.round-tag {
  background: var(--bg-hover);
  color: var(--accent-purple);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.card-summary {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 12px;
}
.card-stats { display: flex; gap: 16px; }

.card-actions {
  display: flex;
  gap: 10px;
  border-top: 1px solid var(--border-default);
  padding-top: 12px;
}
.btn-read {
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: white;
  text-decoration: none;
  transition: all 0.2s;
}
.btn-read:hover { box-shadow: 0 4px 16px rgba(124,58,237,0.3); }
.btn-practice {
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  background: transparent;
  color: var(--accent-purple);
  border: 1px solid rgba(139,92,246,0.2);
  text-decoration: none;
  transition: all 0.2s;
}
.btn-practice:hover {
  border-color: var(--border-hover);
  background: var(--bg-hover);
}

.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
  font-size: 15px;
}
.load-more { text-align: center; padding: 20px; }
.btn-load-more {
  padding: 10px 32px;
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-hover);
  color: var(--accent-purple);
  border:1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-load-more:hover {
  border-color: rgba(139,92,246,0.3);
  background: rgba(139,92,246,0.12);
}
.btn-load-more:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 768px) {
  .hero-section { padding: 36px 16px 32px; }
  .hero-section h1 { font-size: 26px; }
  .main-container { padding: 16px 12px; }
  .filter-section { padding: 14px; }
  .filter-group { flex-direction: column; gap: 6px; }
  .filter-group label { padding-top: 0; }
  .experience-card { padding: 16px; }
  .card-title { font-size: 15px; }
  .card-actions { flex-direction: column; gap: 8px; }
  .btn-read, .btn-practice { text-align: center; }
}
</style>
