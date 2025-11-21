<template>
  <div class="home">
    <el-card class="welcome-card">
      <h1>🤖 Bienvenue sur IroBot</h1>
      <p>RAG Chatbot pour la BEAC</p>
      <p class="version">Version 1.0.0 - Sprint 1 en cours</p>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'Home'
}
</script>

<style lang="scss" scoped>
.home {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #005ca9 0%, #c2a712 100%);
  
  .welcome-card {
    text-align: center;
    padding: 40px;
    
    h1 {
      font-size: 48px;
      margin-bottom: 20px;
      color: #005ca9;
    }
    
    p {
      font-size: 20px;
      color: #606266;
      margin: 10px 0;
    }
    
    .version {
      font-size: 14px;
      color: #909399;
      margin-top: 20px;
    }
  }
}
</style>