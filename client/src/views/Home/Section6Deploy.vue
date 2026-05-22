<template>
  <section class="full-section deploy-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="section-content">
      <div class="section-header">
        <span class="section-badge">部署方案</span>
        <h2 class="section-title">灵活部署，按需选择</h2>
        <p class="section-desc">满足不同场景的使用需求</p>
      </div>

      <div class="deploy-grid">
        <div class="deploy-card">
          <div class="deploy-icon-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
          </div>
          <h3>云服务版</h3>
          <p>开箱即用，无需部署维护</p>
          <ul class="deploy-features">
            <li>自动更新升级</li>
            <li>高可用保障</li>
            <li>弹性扩展</li>
          </ul>
          <span class="deploy-tag">推荐</span>
        </div>

        <div class="deploy-card">
          <div class="deploy-icon-box box-purple">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          </div>
          <h3>私有化部署</h3>
          <p>数据本地化，安全可控</p>
          <ul class="deploy-features">
            <li>数据不出域</li>
            <li>自定义配置</li>
            <li>独立运维</li>
          </ul>
        </div>

        <div class="deploy-card">
          <div class="deploy-icon-box box-green">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </div>
          <h3>开源社区版</h3>
          <p>免费使用，社区支持</p>
          <ul class="deploy-features">
            <li>源码开放</li>
            <li>社区贡献</li>
            <li>自由定制</li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
defineProps<{ observer: (el: HTMLElement | null) => void }>()
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.full-section {
  min-height: calc(100vh - $control-bar-height);
  width: 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-page;
}

.section-content {
  max-width: 1000px;
  width: 100%;
  padding: 60px 40px;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.1s;
}

.visible .section-content {
  opacity: 1;
  transform: translateY(0);
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
}

.section-badge {
  display: inline-block;
  padding: 4px 14px;
  background: rgba($primary, 0.08);
  color: $primary;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 36px;
  font-weight: 800;
  color: $text-title;
  margin-bottom: 12px;
}

.section-desc {
  font-size: 15px;
  color: $text-muted;
}

.deploy-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.deploy-card {
  background: $bg-white;
  padding: 36px 28px;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  text-align: center;
  position: relative;
  transition: all 0.3s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
  }
}

.deploy-icon-box {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: rgba($primary, 0.08);
  color: $primary;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;

  &.box-purple {
    background: rgba(#8b5cf6, 0.08);
    color: #8b5cf6;
  }
  &.box-green {
    background: rgba(#16a34a, 0.08);
    color: #16a34a;
  }
}

.deploy-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: $text-title;
  margin-bottom: 6px;
}

.deploy-card > p {
  font-size: 14px;
  color: $text-muted;
  margin-bottom: 20px;
}

.deploy-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;

  li {
    font-size: 13px;
    color: $text-content;
    padding-left: 20px;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      left: 2px;
      top: 50%;
      transform: translateY(-50%);
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: rgba($primary, 0.3);
    }
  }
}

.deploy-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 3px 10px;
  background: rgba($primary, 0.08);
  color: $primary;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}
</style>
