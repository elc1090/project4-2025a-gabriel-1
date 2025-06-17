<template>
  <div class="login-container">
    <div class="login-box">
      <h1>Bem-vindo à Lousa Colaborativa</h1>
      <p>Faça login para continuar</p>
      <div id="g_id_onload"
           :data-client_id="googleClientId"
           data-callback="handleGoogleSignIn"
           data-auto_select="false">
      </div>
      <div class="g_id_signin"
           data-type="standard"
           data-size="large"
           data-theme="outline"
           data-text="sign_in_with"
           data-shape="rectangular"
           data-logo_alignment="left">
      </div>
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Login',
  data() {
    return {
      errorMessage: '',
      googleClientId: import.meta.env.VITE_GOOGLE_CLIENT_ID,
    };
  },
  methods: {
    async handleGoogleSignIn(response) {
      console.log("Recebida credencial do Google:", response.credential);
      this.errorMessage = '';
      try {
        const res = await fetch('/api/auth/google', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ credential: response.credential }),
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.message || 'Falha no login');
        }

        console.log('Login no backend bem-sucedido:', data.user);
        this.$emit('login-success', data.user);
      } catch (error) {
        console.error('Erro ao fazer login:', error);
        this.errorMessage = `Erro: ${error.message}. Verifique o console para mais detalhes.`;
      }
    }
  },
  mounted() {
    if (!this.googleClientId) {
        console.error("VITE_GOOGLE_CLIENT_ID não está definida no frontend.");
        this.errorMessage = "Erro de configuração do cliente. O login não funcionará.";
    }
    
    // Anexa a função de callback à `window` para que o script do Google possa chamá-la.
    window.handleGoogleSignIn = this.handleGoogleSignIn;
  },
  beforeUnmount() {
    // Limpa a função da `window` quando o componente for destruído para evitar vazamentos de memória.
    delete window.handleGoogleSignIn;
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

.error-message {
  color: #D8000C; /* Vermelho para erro */
  margin-top: 15px;
}
</style> 