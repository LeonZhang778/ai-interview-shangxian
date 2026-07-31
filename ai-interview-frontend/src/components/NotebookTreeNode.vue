<template>
  <div class="notebook-node">
    <div
      class="node-row"
      :class="{ active: node.id === activeId }"
      @click="handleSelect"
      @contextmenu.prevent="showMenu = !showMenu"
    >
      <span class="toggle" v-if="node.children?.length" @click.stop="toggleExpanded">
        {{ expanded ? '▾' : '▸' }}
      </span>
      <span class="toggle placeholder" v-else></span>
      <span class="node-icon">{{ node.icon || '📒' }}</span>
      <span class="node-name">{{ node.name }}</span>
      <span class="node-count" v-if="node.note_count > 0">{{ node.note_count }}</span>
    </div>

    <!-- 右键菜单 -->
    <div v-if="showMenu" class="context-menu" @mouseleave="showMenu = false">
      <div class="menu-item" @click="handleAddChild">添加子笔记本</div>
      <div class="menu-item" @click="handleRename">重命名</div>
      <div class="menu-item" @click="handleExport">导出为 ZIP</div>
      <div class="menu-item danger" @click="handleDelete">删除</div>
    </div>

    <!-- 添加子笔记本 -->
    <div v-if="showAddChild" class="add-form">
      <input
        v-model="childName"
        placeholder="子笔记本名称"
        @keyup.enter="confirmAddChild"
        @blur="cancelAddChild"
        ref="addInput"
        autofocus
      />
    </div>

    <!-- 重命名 -->
    <div v-if="showRename" class="add-form">
      <input
        v-model="renameName"
        :placeholder="node.name"
        @keyup.enter="confirmRename"
        @blur="cancelRename"
        ref="renameInput"
        autofocus
      />
    </div>

    <!-- 子节点 -->
    <div v-if="expanded && node.children?.length" class="node-children">
      <NotebookTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :active-id="activeId"
        @select="(id) => $emit('select', id)"
        @add-child="(parentId) => $emit('add-child', parentId)"
        @rename="(id) => $emit('rename', id)"
        @delete="(id) => $emit('delete', id)"
        @export="(id) => $emit('export', id)"
        @refresh="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  activeId: { type: [Number, null], default: null },
})

const emit = defineEmits(['select', 'add-child', 'rename', 'delete', 'refresh', 'export'])

const expanded = ref(true)
const showMenu = ref(false)
const showAddChild = ref(false)
const showRename = ref(false)
const childName = ref('')
const renameName = ref('')
const addInput = ref(null)
const renameInput = ref(null)

function toggleExpanded() {
  expanded.value = !expanded.value
}

function handleSelect() {
  emit('select', props.node.id)
  showMenu.value = false
}

function handleAddChild() {
  showMenu.value = false
  showAddChild.value = true
  childName.value = ''
  nextTick(() => addInput.value?.focus())
}

async function confirmAddChild() {
  const name = childName.value.trim()
  if (name) {
    emit('add-child', { parentId: props.node.id, name })
  }
  showAddChild.value = false
  childName.value = ''
}

function cancelAddChild() {
  showAddChild.value = false
  childName.value = ''
}

function handleRename() {
  showMenu.value = false
  showRename.value = true
  renameName.value = props.node.name
  nextTick(() => renameInput.value?.focus())
}

async function confirmRename() {
  const name = renameName.value.trim()
  if (name && name !== props.node.name) {
    emit('rename', { id: props.node.id, name })
  }
  showRename.value = false
  renameName.value = ''
}

function cancelRename() {
  showRename.value = false
  renameName.value = ''
}

function handleDelete() {
  showMenu.value = false
  if (confirm(`确定删除笔记本「${props.node.name}」？其中的笔记将移到上一级`)) {
    emit('delete', props.node.id)
  }
}

function handleExport() {
  showMenu.value = false
  emit('export', props.node.id)
}
</script>

<style scoped>
.notebook-node {
  user-select: none;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 13px;
  color: var(--text-secondary);
  position: relative;
}
.node-row:hover {
  background: rgba(255, 255, 255, 0.06);
}
.node-row.active {
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-light);
}

.toggle {
  width: 14px;
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
  text-align: center;
}
.toggle.placeholder {
  visibility: hidden;
}

.node-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  flex-shrink: 0;
}

.node-children {
  padding-left: 16px;
}

/* 右键菜单 */
.context-menu {
  position: absolute;
  z-index: 100;
  background: rgba(30, 30, 40, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 130px;
}
.menu-item {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-secondary);
}
.menu-item:hover {
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-light);
}
.menu-item.danger:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

/* 内联编辑表单 */
.add-form {
  padding: 4px 8px 4px 24px;
}
.add-form input {
  width: 100%;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
</style>