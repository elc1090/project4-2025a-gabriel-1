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

<script setup>
import { ref, onMounted, defineEmits } from 'vue';

const emit = defineEmits(['login-success']);

const errorMessage = ref('');
const googleClientId = ref(import.meta.env.VITE_GOOGLE_CLIENT_ID);

const handleGoogleSignIn = async (response) => {
  console.log("Recebida credencial do Google:", response.credential);
  errorMessage.value = '';
  try {
    // A URL da API deve ser a URL do seu backend, que pode estar rodando localmente ou em um servidor.
    // Usar um caminho relativo /api/auth/google só funciona se o servidor de desenvolvimento do Vite (ou um servidor web de produção)
    // estiver configurado para fazer proxy das requisições para o backend Flask.
    const apiUrl = import.meta.env.VITE_API_URL || 'https://project3-2025a-gabriel.onrender.com'; // Use a variável de ambiente ou um caminho relativo
    const res = await fetch(`${apiUrl}/api/auth/google`, {
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
    emit('login-success', data.user);
  } catch (error) {
    console.error('Erro ao fazer login:', error);
    errorMessage.value = `Erro: ${error.message}. Verifique o console para mais detalhes.`;
  }
};

onMounted(() => {
  if (!googleClientId.value) {
      console.error("VITE_GOOGLE_CLIENT_ID não está definida no frontend.");
      errorMessage.value = "Erro de configuração do cliente. O login não funcionará.";
  }
  
  // O script do Google espera que a função de callback esteja no escopo global (window).
  // No <script setup>, as funções não são expostas automaticamente.
  // Precisamos anexá-la explicitamente ao objeto window.
  window.handleGoogleSignIn = handleGoogleSignIn;
});

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