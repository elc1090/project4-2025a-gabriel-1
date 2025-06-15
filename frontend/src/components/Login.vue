<template>
  <div class="login-container">
    <div class="login-box">
      <h1>Bem-vindo à Lousa Colaborativa</h1>
      <p>Faça login para continuar</p>
      <button @click="loginWithGoogle" class="google-login-button">
        <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google Logo" />
        Entrar com Google
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Login',
  methods: {
    loginWithGoogle() {
      // A funcionalidade de login será implementada futuramente
      console.log('Tentativa de login com Google');
    }
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.login-box {
  text-align: center;
  background-color: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 24px;
  margin-bottom: 10px;
}

p {
  margin-bottom: 20px;
  color: #666;
}

.google-login-button {
  display: inline-flex;
  align-items: center;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  background-color: #4285F4;
  color: white;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.google-login-button:hover {
  background-color: #357ae8;
}

.google-login-button img {
  width: 20px;
  height: 20px;
  margin-right: 10px;
  background-color: white;
  border-radius: 50%;
  padding: 2px;
}
</style> 