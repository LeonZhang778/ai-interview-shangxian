<template>
  <StarryBackground />
  <div class="my-collections-page">
    <div class="page-header">
      <h1>我的收藏</h1>
      <p class="header-desc">管理你收藏的面经，按分组整理更高效</p>
    </div>

    <div class="main-container">
      <!-- 分组标签栏 -->
      <div class="group-tabs">
        <div class="group-tabs-inner">
          <span
            class="group-tab"
            :class="{ active: activeGroupId === null }"
            @click="switchGroup(null)"
          >
            全部
            <span class="group-count">{{ totalCount }}</span>
          </span>
          <span
            class="group-tab"
            :class="{ active: activeGroupId === 0 }"
            @click="switchGroup(0)"
          >
            未分组
            <span class="group-count">{{ ungroupedCount }}</span>
          </span>
          <span
            v-for="g in groups"
            :key="g.id"
            class="group-tab"
            :class="{ active: activeGroupId === g.id }"
            @click="switchGroup(g.id)"
          >
            <template v-if="editingGroupId === g.id">
              <input
                v-model="editingName"
                class="group-name-input"
                @blur="saveGroupName(g.id)"
                @keyup.enter="saveGroupName(g.id)"
                @keyup.escape="cancelEditGroup"
                ref="editInput"
                maxlength="20"
              />
            </template>
            <template v-else>
              {{ g.name }}
              <span class="group-count">{{ g.count }}</span>
              <span class="group-actions" @click.stop>
                <span class="group-action" @click="startEditGroup(g)" title="重命名"><BaseIcon name="pencil" :size="14" /></span>
                <span class="group-action" @click="confirmDeleteGroup(g)" title="删除"><BaseIcon name="trash" :size="14" /></span>
              </span>
            </template>
          </span>
          <span class="group-tab group-add" @click="showAddGroup = true" v-if="!showAddGroup">
            + 新建分组
          </span>
          <span class="group-tab group-add-input" v-else>
            <input
              v-model="newGroupName"
              class="group-name-input"
              placeholder="分组名称"
              @blur="handleAddGroupBlur"
              @keyup.enter="createGroup"
              @keyup.escape="cancelAddGroup"
              ref="addGroupInput"
              maxlength="20"
            />
          </span>
        </div>
      </div>

      <!-- 收藏列表 -->
      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-else-if="collections.length === 0" class="empty-state">
        <div class="empty-icon"><BaseIcon name="star" :size="40" /></div>
        <p>还没有收藏面经</p>
        <router-link to="/experiences" class="btn-browse">去逛逛</router-link>
      </div>

      <div v-else class="collections-grid">
        <div
          v-for="item in collections"
          :key="item.experience.id"
          class="collection-card"
        >
          <div class="card-top">
            <router-link :to="`/experiences/${item.experience.id}`" class="card-title">
              {{ item.experience.title }}
            </router-link>
            <div class="card-meta">
              <span class="meta-company">{{ item.experience.company }}</span>
              <span class="meta-position">{{ item.experience.position }}</span>
            </div>
            <p class="card-summary" v-if="item.experience.summary">{{ item.experience.summary }}</p>
            <div class="card-tags" v-if="item.experience.tags?.length">
              <span v-for="tag in item.experience.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
          <div class="card-bottom">
            <div class="card-stats">
              <span><BaseIcon name="eye" :size="14" /> {{ item.experience.view_count }}</span>
              <span><BaseIcon name="thumbs-up" :size="14" /> {{ item.experience.like_count }}</span>
              <span><BaseIcon name="star-fill" :size="14" /> {{ item.experience.collect_count }}</span>
            </div>
            <div class="card-group-move">
              <select
                :value="item.group_id || ''"
                @change="handleMove(item.experience.id, $event.target.value)"
                class="group-select"
              >
                <option value="">未分组</option>
                <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <button
          class="page-btn"
          :disabled="currentPage <= 1"
          @click="changePage(currentPage - 1)"
        >上一页</button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="page-btn"
          :disabled="currentPage >= totalPages"
          @click="changePage(currentPage + 1)"
        >下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import StarryBackground from '../components/StarryBackground.vue'
import {
  getMyCollections,
  getCollectionGroups,
  createCollectionGroup,
  updateCollectionGroup,
  deleteCollectionGroup,
  moveCollection
} from '../api/experience'

const collections = ref([])
const groups = ref([])
const loading = ref(true)
const activeGroupId = ref(null)
const currentPage = ref(1)
const pageSize = 20
const totalCount = ref(0)
const ungroupedCount = ref(0)
const showAddGroup = ref(false)
const newGroupName = ref('')
const editingGroupId = ref(null)
const editingName = ref('')
const addGroupInput = ref(null)
const editInput = ref(null)

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

async function loadData() {
  loading.value = true
  try {
    const params = { page: currentPage.value, size: pageSize }
    if (activeGroupId.value !== null) params.group_id = activeGroupId.value

    const [collectionsRes, groupsRes] = await Promise.all([
      getMyCollections(params),
      getCollectionGroups()
    ])

    collections.value = collectionsRes.items || []
    totalCount.value = collectionsRes.total || 0
    groups.value = groupsRes.groups || []
    ungroupedCount.value = groupsRes.ungrouped_count || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function switchGroup(groupId) {
  activeGroupId.value = groupId
  currentPage.value = 1
  loadData()
}

function changePage(page) {
  currentPage.value = page
  loadData()
}

async function handleMove(experienceId, groupId) {
  try {
    await moveCollection(experienceId, groupId || null)
    loadData()
  } catch (e) {
    console.error(e)
  }
}

async function createGroup() {
  const name = newGroupName.value.trim()
  if (!name) {
    cancelAddGroup()
    return
  }
  try {
    await createCollectionGroup(name)
    newGroupName.value = ''
    showAddGroup.value = false
    loadData()
  } catch (e) {
    console.error(e)
  }
}

function handleAddGroupBlur() {
  setTimeout(() => { createGroup() }, 100)
}

function cancelAddGroup() {
  newGroupName.value = ''
  showAddGroup.value = false
}

function startEditGroup(group) {
  editingGroupId.value = group.id
  editingName.value = group.name
  nextTick(() => {
    if (editInput.value?.[0]) editInput.value[0].focus()
  })
}

async function saveGroupName(groupId) {
  const name = editingName.value.trim()
  if (!name) {
    cancelEditGroup()
    return
  }
  try {
    await updateCollectionGroup(groupId, { name })
    editingGroupId.value = null
    editingName.value = ''
    loadData()
  } catch (e) {
    console.error(e)
  }
}

function cancelEditGroup() {
  editingGroupId.value = null
  editingName.value = ''
}

async function confirmDeleteGroup(group) {
  if (!confirm(`确定删除分组「${group.name}」？分组内的收藏不会被删除。`)) return
  try {
    await deleteCollectionGroup(group.id)
    if (activeGroupId.value === group.id) activeGroupId.value = null
    loadData()
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadData)
</script>

<style scoped>
.my-collections-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.page-header {
  text-align: center;
  padding: 40px 20px 20px;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);

  background-clip: text;
  margin-bottom: 8px;
}
.header-desc {
  font-size: 14px;
  color: var(--text-muted);
}
.main-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 分组标签 */
.group-tabs {
  margin-bottom: 24px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.group-tabs-inner {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  min-width: max-content;
}
.group-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.group-tab:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}
.group-tab.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: var(--bg-base);
}
.group-count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--bg-hover);
  color: var(--text-muted);
}
.group-tab.active .group-count {
  background: var(--bg-base);
  color: var(--accent-primary);
}
.group-actions {
  display: inline-flex;
  gap: 2px;
  margin-left: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.group-tab:hover .group-actions {
  opacity: 1;
}
.group-action {
  cursor: pointer;
  font-size: 12px;
  padding: 2px;
  border-radius: 4px;
  transition: background 0.2s;
}
.group-action:hover {
  background: var(--bg-hover);
}
.group-add {
  border-style: dashed;
  color: var(--text-muted);
}
.group-add:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}
.group-name-input {
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 13px;
  width: 80px;
  padding: 0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.btn-browse {
  display: inline-block;
  margin-top: 16px;
  padding: 10px 24px;
  background: var(--accent-primary); color: var(--bg-base);
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}
.loading-state {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
}

/* 收藏卡片 */
.collections-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.collection-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
}
.collection-card:hover {
  border-color: var(--border-hover);
  background: var(--bg-hover);
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  text-decoration: none;
  display: block;
  margin-bottom: 8px;
}
.card-title:hover {
  color: var(--accent-primary);
}
.card-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.meta-company, .meta-position {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-hover);
  color: var(--accent-primary);
}
.meta-position {
  background: var(--bg-hover);
  color: var(--text-secondary);
}
.card-summary {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-hover);
  color: var(--text-muted);
}
.card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--border-default);
}
.card-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
.group-select {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 4px 8px;
  outline: none;
  cursor: pointer;
}
.group-select option {
  background: var(--bg-input);
  color: var(--text-primary);
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}
.page-btn {
  padding: 8px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.page-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
