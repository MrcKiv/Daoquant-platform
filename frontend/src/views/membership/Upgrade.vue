<!-- views/membership/Upgrade.vue -->
<template>
  <div class="upgrade-container">
    <FixedNavbar />

    <div class="upgrade-content">
      <div class="upgrade-header">
        <h1>会员升级</h1>
        <p>解锁更多高级功能，提升您的策略开发体验</p>
        <el-alert
          v-if="currentLevel === 'admin'"
          title="管理员账号已拥有最高权限，无需升级。"
          type="success"
          :closable="false"
          class="admin-alert"
        />
      </div>

      <div class="membership-plans">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="plan-card free" :class="{ active: currentLevel === 'free' }">
              <div class="plan-header">
                <h3>免费用户</h3>
                <div class="price">$0<span>/永久</span></div>
              </div>
              <ul class="plan-features">
                <li><i class="el-icon-check"></i> 基础策略浏览</li>
                <li><i class="el-icon-check"></i> 策略回测查看</li>
<!--                <li><i class="el-icon-close"></i> 新建策略</li>-->
                <li><i class="el-icon-close"></i> AI策略推荐</li>
                <li><i class="el-icon-close"></i> 高级分析工具</li>
              </ul>
              <el-button
                type="info"
                disabled
                v-if="currentLevel === 'free'"
              >
                当前等级
              </el-button>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card class="plan-card basic" :class="{ active: currentLevel === 'basic' }">
              <div class="plan-header">
                <h3>基础会员</h3>
                <div class="price">$69.9<span>/月</span></div>
                <el-tag type="success" v-if="currentLevel === 'basic'">当前等级</el-tag>
              </div>
              <ul class="plan-features">
                <li><i class="el-icon-check"></i> 免费用户所有功能</li>
<!--                <li><i class="el-icon-check"></i> 新建策略</li>-->
                <li><i class="el-icon-check"></i> 策略参数配置</li>
                <li><i class="el-icon-check"></i> 策略分享</li>
                <li><i class="el-icon-close"></i> AI策略推荐</li>
                <li><i class="el-icon-close"></i> 高级分析工具</li>
              </ul>
              <el-button
                type="primary"
                @click="selectPlan('basic')"
                :disabled="!canUpgradeTo('basic')"
                v-if="currentLevel !== 'basic'"
              >
                {{ getUpgradeButtonText('basic') }}
              </el-button>
              <el-button
                type="success"
                disabled
                v-else
              >
                当前等级
              </el-button>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card class="plan-card premium" :class="{ active: currentLevel === 'premium' }">
              <div class="plan-header">
                <h3>高级会员</h3>
                <div class="price">$399.9<span>/月</span></div>
                <el-tag type="success" v-if="currentLevel === 'premium'">当前等级</el-tag>
              </div>
              <ul class="plan-features">
                <li><i class="el-icon-check"></i> 基础会员所有功能</li>
                <li><i class="el-icon-check"></i> AI策略推荐</li>
                <li><i class="el-icon-check"></i> 高级分析工具</li>
                <li><i class="el-icon-check"></i> 策略优化建议</li>
                <li><i class="el-icon-check"></i> 优先技术支持</li>
                <li><i class="el-icon-close"></i> VIP专属策略</li>
              </ul>
              <el-button
                type="primary"
                @click="selectPlan('premium')"
                :disabled="!canUpgradeTo('premium')"
                v-if="currentLevel !== 'premium'"
              >
                {{ getUpgradeButtonText('premium') }}
              </el-button>
              <el-button
                type="success"
                disabled
                v-else
              >
                当前等级
              </el-button>
            </el-card>
          </el-col>

          <el-col :span="6">
            <el-card class="plan-card vip" :class="{ active: currentLevel === 'vip' }">
              <div class="plan-header">
                <h3>VIP会员</h3>
                <div class="price">$999.9<span>/月</span></div>
                <el-tag type="success" v-if="currentLevel === 'vip'">当前等级</el-tag>
              </div>
              <ul class="plan-features">
                <li><i class="el-icon-check"></i> 高级会员所有功能</li>
                <li><i class="el-icon-check"></i> VIP专属策略</li>
                <li><i class="el-icon-check"></i> 一对一专家咨询</li>
                <li><i class="el-icon-check"></i> 最新功能优先体验</li>
                <li><i class="el-icon-check"></i> 专属客服支持</li>
                <li><i class="el-icon-check"></i> 定制化策略开发</li>
              </ul>
              <el-button
                type="primary"
                @click="selectPlan('vip')"
                :disabled="!canUpgradeTo('vip')"
                v-if="currentLevel !== 'vip'"
              >
                {{ getUpgradeButtonText('vip') }}
              </el-button>
              <el-button
                type="success"
                disabled
                v-else
              >
                当前等级
              </el-button>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <div class="upgrade-actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-button @click="goBack">返回上一页</el-button>
      </div>
    </div>

    <Lastone />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import FixedNavbar from '@/components/common/FixedNavbar.vue'
import Lastone from '@/components/common/Lastone.vue'

const router = useRouter()
const userStore = useUserStore()

// 当前用户等级
const currentLevel = computed(() => {
  return userStore.membershipLevel || 'free'
})

// 等级层级映射
const levelHierarchy = {
  'free': 0,
  'basic': 1,
  'premium': 2,
  'vip': 3,
  'admin': 4
}

// 检查是否可以升级到指定等级
const canUpgradeTo = (level) => {
  const currentLevelValue = levelHierarchy[currentLevel.value] || 0
  const targetLevelValue = levelHierarchy[level] || 0
  return targetLevelValue > currentLevelValue
}

// 获取升级按钮文本
const getUpgradeButtonText = (level) => {
  if (currentLevel.value === level) {
    return '当前等级'
  }
  return canUpgradeTo(level) ? '立即升级' : '无法降级'
}

// 选择升级计划
const selectPlan = async (level) => {
  try {
    // 这里可以调用实际的支付接口
    // 模拟支付成功后的处理
    ElMessage.success(`成功升级到${getLevelName(level)}！`)

    // 更新用户Store中的等级信息
    userStore.updateUserInfo({
      membership_level: level
    })

    // 重新检查权限并跳转
    setTimeout(() => {
      router.go(-1) // 返回上一页
    }, 1000)
  } catch (error) {
    ElMessage.error('升级失败: ' + (error.response?.data?.error || '未知错误'))
  }
}

// 获取等级名称
const getLevelName = (level) => {
  const names = {
    'free': '免费用户',
    'basic': '基础会员',
    'premium': '高级会员',
    'vip': 'VIP会员',
    'admin': '管理员'
  }
  return names[level] || level
}

// 返回首页
const goHome = () => {
  router.push('/')
}

// 返回上一页
const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
.upgrade-container {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.upgrade-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 80px 20px 40px;
}

.upgrade-header {
  text-align: center;
  margin-bottom: 40px;
}

.upgrade-header h1 {
  font-size: 32px;
  color: #333;
  margin-bottom: 10px;
}

.upgrade-header p {
  font-size: 16px;
  color: #666;
}

.admin-alert {
  margin: 20px auto 0;
  max-width: 520px;
}

.membership-plans {
  margin-bottom: 40px;
}

.plan-card {
  height: 100%;
  transition: all 0.3s;
  border: 2px solid #ebeef5;
}

.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.plan-card.active {
  border-color: #409EFF;
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.2);
}

.plan-header {
  text-align: center;
  margin-bottom: 20px;
  position: relative;
}

.plan-header h3 {
  font-size: 20px;
  margin-bottom: 10px;
  color: #333;
}

.price {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.price span {
  font-size: 14px;
  font-weight: normal;
  color: #999;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 20px 0;
}

.plan-features li {
  padding: 8px 0;
  display: flex;
  align-items: center;
}

.plan-features li i {
  margin-right: 8px;
  font-size: 16px;
}

.plan-features li i.el-icon-check {
  color: #67C23A;
}

.plan-features li i.el-icon-close {
  color: #F56C6C;
}

.plan-card.free .plan-header h3 {
  color: #909399;
}

.plan-card.basic .plan-header h3 {
  color: #409EFF;
}

.plan-card.premium .plan-header h3 {
  color: #67C23A;
}

.plan-card.vip .plan-header h3 {
  color: #E6A23C;
}

.upgrade-actions {
  text-align: center;
}

.upgrade-actions .el-button {
  margin: 0 10px;
}
</style>
