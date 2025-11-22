<template>
  <div class="home-page">
    <h1>🏠 Page d'accueil</h1>
    <p>Cette page sera développée dans les prochains sprints.</p>
    <el-alert
      title="En construction"
      type="info"
      description="Les fonctionnalités de chat, historique, et documents seront ajoutées prochainement."
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup>
import { ElAlert } from 'element-plus'
</script>

<style scoped>
.home-page {
  padding: 40px;
}

h1 {
  margin-bottom: 16px;
  color: var(--text-primary);
}

p {
  margin-bottom: 24px;
  color: var(--text-secondary);
}
</style>