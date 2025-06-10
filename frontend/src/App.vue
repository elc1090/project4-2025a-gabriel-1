<template>
  <div id="app-container">
    <DrawingCanvas />
  </div>
</template>

<script setup>
import DrawingCanvas from './components/DrawingCanvas.vue';
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