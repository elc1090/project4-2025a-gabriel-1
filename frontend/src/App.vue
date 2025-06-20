<template>
  <div id="app-container">
    <Login v-if="!userInfo.isLoggedIn" />
    <template v-else>
      <WhiteboardMenu 
        @whiteboard-selected="handleWhiteboardSelected"
        @toggle-shape-recognition="handleToggleShapeRecognition"
        :shape-recognition-enabled="shapeRecognitionEnabled"
      />
      <DrawingCanvas 
        v-if="selectedWhiteboardId" 
        :key="selectedWhiteboardId" 
        :whiteboardId="selectedWhiteboardId"
        :shape-recognition-enabled="shapeRecognitionEnabled"
      />
      <div v-else class="placeholder-canvas">
        <h1>Selecione ou crie uma lousa para começar</h1>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { userInfo } from './services/userInfo.js';
import Login from './components/Login.vue';
import DrawingCanvas from './components/DrawingCanvas.vue';
import WhiteboardMenu from './components/WhiteboardMenu.vue';

const selectedWhiteboardId = ref(null);
const shapeRecognitionEnabled = ref(false);

const handleWhiteboardSelected = (whiteboardId) => {
  console.log("App.vue: Whiteboard selected:", whiteboardId);
  selectedWhiteboardId.value = whiteboardId;
};

const handleToggleShapeRecognition = (value) => {
  shapeRecognitionEnabled.value = value;
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
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #f0f2f5;
}

.placeholder-canvas {
  flex-grow: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #888;
  background-color: #ffffff;
  border-left: 1px solid #ddd;
}
</style>