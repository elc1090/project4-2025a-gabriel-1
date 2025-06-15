<template>
  <div id="app-container">
    <Login v-if="!user" @login-success="onLoginSuccess" />
    <DrawingCanvas v-else :user="user" />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import Login from './components/Login.vue';
import DrawingCanvas from './components/DrawingCanvas.vue';

const user = ref(null);

const onLoginSuccess = (userData) => {
  console.log('Login bem-sucedido no App.vue, mostrando o canvas.', userData);
  user.value = userData;
};
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  max-width: none !important;
  text-align: left !important;
  display: block !important;
}

html, body {
  overflow: hidden; 
}

body {
  background-color: #333;
}

#app-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
}

</style>