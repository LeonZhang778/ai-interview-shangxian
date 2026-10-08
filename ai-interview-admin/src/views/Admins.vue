<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="font-size:20px">管理员管理</h1>
      <div style="display:flex;gap:12px;align-items:center">
        <input v-model="emailFilter" placeholder="搜索邮箱..." style="width:200px" @input="debouncedSearch" />
        <button class="btn-primary btn-sm" @click="openCreate">+ 新建管理员</button>
      </div>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>邮箱</th>
            <th>姓名</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in admins" :key="a.id">
            <td>{{ a.id }}</td>
            <td>{{ a.email }}</td>
            <td>{{ a.first_name || '' }} {{ a.last_name || '' }}</td>
            <td><span :class="['badge', a.is_active ? 'badge-green' : 'badge-red']">{{ a.is_active ? '正常' : '禁用' }}</span></td>
            <td>{{ formatDate(a.created_at) }}</td>
            <td class="action-cell">
              <button class="btn-primary btn-sm" @click="openEdit(a)">编辑</button>
              <button class="btn-sm btn-primary" @click="openChangePassword(a)">改密码</button>
              <button class="btn-sm btn-primary" @click="openResetPassword(a)">重置密码</button>
              <button class="btn-danger btn-sm" @click="openDelete(a)">删除</button>
            </td>
          </tr>
          <tr v-if="admins.length === 0">
            <td colspan="6" style="text-align:center;color:#9ca3af;padding:40px">暂无数据</td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--; loadAdmins()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++; loadAdmins()">下一页</button>
      </div>
    </div>

    <!-- Create Modal -->
    <div class="modal-mask" v-if="showCreate" @click.self="showCreate = false">
      <div class="modal">
        <h3>新建管理员</h3>
        <div class="form-group">
          <label>邮箱</label>
          <input v-model="createForm.email" type="email" placeholder="admin@example.com" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>名</label>
            <input v-model="createForm.first_name" placeholder="名" />
          </div>
          <div class="form-group">
            <label>姓</label>
            <input v-model="createForm.last_name" placeholder="姓" />
          </div>
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="createForm.password" type="password" placeholder="至少8位" />
        </div>
        <p v-if="modalError" class="error">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="btn-sm" style="background:var(--admin-bg-muted);color:var(--admin-text-secondary)" @click="showCreate = false">取消</button>
          <button class="btn-primary btn-sm" :disabled="modalLoading" @click="handleCreate">{{ modalLoading ? '提交中...' : '确认创建' }}</button>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div class="modal-mask" v-if="showEdit" @click.self="showEdit = false">
      <div class="modal">
        <h3>编辑管理员</h3>
        <div class="form-group">
          <label>邮箱</label>
          <input v-model="editForm.email" type="email" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>名</label>
            <input v-model="editForm.first_name" />
          </div>
          <div class="form-group">
            <label>姓</label>
            <input v-model="editForm.last_name" />
          </div>
        </div>
        <div class="form-group">
          <label style="display:flex;align-items:center;gap:8px">
            <input type="checkbox" v-model="editForm.is_active" style="width:auto" />
            启用状态
          </label>
        </div>
        <p v-if="modalError" class="error">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="btn-sm" style="background:var(--admin-bg-muted);color:var(--admin-text-secondary)" @click="showEdit = false">取消</button>
          <button class="btn-primary btn-sm" :disabled="modalLoading" @click="handleEdit">{{ modalLoading ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- Change Password Modal -->
    <div class="modal-mask" v-if="showChangePwd" @click.self="showChangePwd = false">
      <div class="modal">
        <h3>修改密码</h3>
        <p class="modal-desc">管理员: {{ changePwdTarget?.email }}</p>
        <div class="form-group">
          <label>当前密码</label>
          <input v-model="changePwdForm.current_password" type="password" placeholder="输入当前密码" />
        </div>
        <div class="form-group">
          <label>新密码</label>
          <input v-model="changePwdForm.new_password" type="password" placeholder="至少8位" />
        </div>
        <p v-if="modalError" class="error">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="btn-sm" style="background:var(--admin-bg-muted);color:var(--admin-text-secondary)" @click="showChangePwd = false">取消</button>
          <button class="btn-primary btn-sm" :disabled="modalLoading" @click="handleChangePassword">{{ modalLoading ? '提交中...' : '确认修改' }}</button>
        </div>
      </div>
    </div>

    <!-- Reset Password Modal -->
    <div class="modal-mask" v-if="showResetPwd" @click.self="showResetPwd = false">
      <div class="modal">
        <h3>重置密码</h3>
        <p class="modal-desc">管理员: {{ resetPwdTarget?.email }}</p>
        <div class="form-group">
          <label>新密码</label>
          <input v-model="resetPwdForm.password" type="password" placeholder="至少8位" />
        </div>
        <p v-if="modalError" class="error">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="btn-sm" style="background:var(--admin-bg-muted);color:var(--admin-text-secondary)" @click="showResetPwd = false">取消</button>
          <button class="btn-sm btn-primary" :disabled="modalLoading" @click="handleResetPassword">{{ modalLoading ? '提交中...' : '确认重置' }}</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <div class="modal-mask" v-if="showDelete" @click.self="showDelete = false">
      <div class="modal">
        <h3>确认删除</h3>
        <p class="modal-desc">确定要删除管理员 <strong>{{ deleteTarget?.email }}</strong> 吗？此操作不可撤销。</p>
        <p v-if="modalError" class="error">{{ modalError }}</p>
        <div class="modal-actions">
          <button class="btn-sm" style="background:var(--admin-bg-muted);color:var(--admin-text-secondary)" @click="showDelete = false">取消</button>
          <button class="btn-danger btn-sm" :disabled="modalLoading" @click="confirmDelete">{{ modalLoading ? '删除中...' : '确认删除' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { adminApi } from '../api'

const admins = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const emailFilter = ref('')
let searchTimer = null

const showCreate = ref(false)
const showEdit = ref(false)
const showChangePwd = ref(false)
const showResetPwd = ref(false)
const showDelete = ref(false)
const modalLoading = ref(false)
const modalError = ref('')

const createForm = reactive({ email: '', first_name: '', last_name: '', password: '' })
const editForm = reactive({ id: null, email: '', first_name: '', last_name: '', is_active: true })
const changePwdTarget = ref(null)
const changePwdForm = reactive({ current_password: '', new_password: '' })
const resetPwdTarget = ref(null)
const resetPwdForm = reactive({ password: '' })
const deleteTarget = ref(null)

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN')
}

async function loadAdmins() {
  try {
    const data = await adminApi.list({ page: page.value, per_page: perPage, email: emailFilter.value || undefined })
    admins.value = data.items
    total.value = data.total
  } catch (e) { console.error(e) }
}

function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadAdmins() }, 300)
}

function resetModal() {
  modalError.value = ''
  modalLoading.value = false
}

function openCreate() {
  resetModal()
  Object.assign(createForm, { email: '', first_name: '', last_name: '', password: '' })
  showCreate.value = true
}

function openEdit(admin) {
  resetModal()
  Object.assign(editForm, { id: admin.id, email: admin.email, first_name: admin.first_name || '', last_name: admin.last_name || '', is_active: admin.is_active })
  showEdit.value = true
}

function openChangePassword(admin) {
  resetModal()
  changePwdTarget.value = admin
  Object.assign(changePwdForm, { current_password: '', new_password: '' })
  showChangePwd.value = true
}

function openResetPassword(admin) {
  resetModal()
  resetPwdTarget.value = admin
  resetPwdForm.password = ''
  showResetPwd.value = true
}

function openDelete(admin) {
  resetModal()
  deleteTarget.value = admin
  showDelete.value = true
}

async function handleCreate() {
  modalError.value = ''
  if (!createForm.email || !createForm.password) { modalError.value = '邮箱和密码为必填项'; return }
  if (createForm.password.length < 8) { modalError.value = '密码至少8位'; return }
  modalLoading.value = true
  try {
    await adminApi.create({ ...createForm })
    showCreate.value = false
    await loadAdmins()
  } catch (e) { modalError.value = e.message }
  finally { modalLoading.value = false }
}

async function handleEdit() {
  modalError.value = ''
  if (!editForm.email) { modalError.value = '邮箱为必填项'; return }
  modalLoading.value = true
  try {
    await adminApi.update(editForm.id, { email: editForm.email, first_name: editForm.first_name || null, last_name: editForm.last_name || null, is_active: editForm.is_active })
    showEdit.value = false
    await loadAdmins()
  } catch (e) { modalError.value = e.message }
  finally { modalLoading.value = false }
}

async function handleChangePassword() {
  modalError.value = ''
  if (!changePwdForm.current_password || !changePwdForm.new_password) { modalError.value = '请填写完整'; return }
  if (changePwdForm.new_password.length < 8) { modalError.value = '新密码至少8位'; return }
  modalLoading.value = true
  try {
    await adminApi.changePassword(changePwdTarget.value.id, { ...changePwdForm })
    showChangePwd.value = false
    alert('密码修改成功')
  } catch (e) { modalError.value = e.message }
  finally { modalLoading.value = false }
}

async function handleResetPassword() {
  modalError.value = ''
  if (!resetPwdForm.password) { modalError.value = '请填写新密码'; return }
  if (resetPwdForm.password.length < 8) { modalError.value = '密码至少8位'; return }
  modalLoading.value = true
  try {
    await adminApi.resetPassword(resetPwdTarget.value.id, { password: resetPwdForm.password })
    showResetPwd.value = false
    alert('密码重置成功')
  } catch (e) { modalError.value = e.message }
  finally { modalLoading.value = false }
}

async function confirmDelete() {
  modalError.value = ''
  modalLoading.value = true
  try {
    await adminApi.delete(deleteTarget.value.id)
    showDelete.value = false
    await loadAdmins()
  } catch (e) { modalError.value = e.message }
  finally { modalLoading.value = false }
}

onMounted(loadAdmins)
</script>

<style scoped>
.action-cell { white-space: nowrap; }
.action-cell button { margin-right: 6px; }
.action-cell button:last-child { margin-right: 0; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 16px 0 0; font-size: 13px; color: var(--admin-text-secondary); }

.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4); display: flex; align-items: center;
  justify-content: center; z-index: 1000;
}
.modal {
  background: var(--admin-bg-card); border: 1px solid var(--admin-border); border-radius: var(--admin-radius-lg); padding: 28px; width: 440px;
  box-shadow: var(--admin-shadow-md);
}
.modal h3 { font-size: 18px; margin-bottom: 20px; color: var(--admin-text-primary); }
.modal-desc { font-size: 13px; color: var(--admin-text-secondary); margin-bottom: 16px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.error { color: var(--admin-text-primary); font-size: 13px; margin-top: 8px; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 500; color: var(--admin-text-primary); }
.form-group input { width: 100%; padding: 9px 12px; border: 1px solid var(--admin-border); border-radius: var(--admin-radius-md); font-size: 14px; outline: none; transition: all 0.2s; background: var(--admin-bg-content); color: var(--admin-text-primary); }
.form-group input:focus { border-color: var(--admin-primary); box-shadow: 0 0 0 3px var(--admin-primary-soft); background: var(--admin-bg-content); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
