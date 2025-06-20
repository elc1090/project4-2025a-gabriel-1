<template>
  <div class="canvas-ui-container">
    <div class="left-controls">
      <WhiteboardMenu
        :selected-board-id="currentBoardId"
        @board-selected="handleBoardSelected"
        @board-created="handleBoardSelected"
        @board-deleted="handleBoardDeleted"
      />
      <div class="undo-redo-container">
        <button @click="undo" :disabled="!canUndo" title="Desfazer (Ctrl+Z)">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-corner-up-left"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 0 0-4-4H4"></path></svg>
        </button>
        <button @click="redo" :disabled="!canRedo" title="Refazer (Ctrl+Y)">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-corner-up-right"><polyline points="15 14 20 9 15 4"></polyline><path d="M4 20v-7a4 4 0 0 1 4-4h12"></path></svg>
        </button>
      </div>
    </div>
  </div>
  <canvas
    ref="viewportCanvasRef"
    @mousedown="handleMouseDown"
    @mousemove="handleMouseMove"
    @mouseup="handleMouseUp"
    @mouseout="handleMouseOut"
    @wheel.prevent="handleWheel"
    @touchstart.prevent="handleTouchStart"
    @touchmove.prevent="handleTouchMove"
    @touchend="handleTouchEnd"
    @touchcancel="handleTouchEnd"
    @contextmenu.prevent="showContextMenu"
    class="viewport-canvas"
  ></canvas>
  <ContextMenu
    v-if="menu.visible"
    :x="menu.x"
    :y="menu.y"
    @select="handleMenuSelection"
  />
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue';
import ContextMenu from './ContextMenu.vue';
import WhiteboardMenu from './WhiteboardMenu.vue';
import { userInfo } from '../services/userInfo';
import { io } from 'socket.io-client';

const props = defineProps({
  user: Object,
});

const socket = ref(null);
const currentBoardId = ref(1);

const viewportCanvasRef = ref(null);
let ctx = null;

const WORLD_WIDTH = 1000;
const WORLD_HEIGHT = 1000;
const WORLD_BACKGROUND_COLOR = '#FFFFFF';
const TARGET_VIEWPORT_ASPECT_RATIO = (800 / 600);

const viewportState = reactive({
  width: 800,
  height: 600,
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  isPanning: false,
  lastPanX: 0,
  lastPanY: 0,
});

const strokes = ref([]);
const redoStack = ref([]);
let isDrawing = false;
let currentTempStrokeId = null;

const drawingSettings = reactive({
  color: 'black',
  lineWidth: 3,
});

const menu = reactive({
  visible: false,
  x: 0,
  y: 0,
});

const longPressDuration = 700;
let longPressTimer = null;
let touchStartCoords = { x: 0, y: 0, time: 0 };
const longPressMoveThreshold = 10;

let isMultiTouching = false;
let initialGestureInfo = {
  pinchDistance: 0,
  midpoint: { x: 0, y: 0 },
  worldMidpoint: { x: 0, y: 0},
  offsetX: 0,
  offsetY: 0,
  scale: 1,
};

const canUndo = computed(() => {
  return strokes.value.some(s => s.user_id === userInfo.value?.id);
});

const canRedo = computed(() => {
  return redoStack.value.length > 0;
});

const undo = () => {
  if (!canUndo.value) return;
  socket.value.emit('undo_request', { 
    user_email: userInfo.value.email,
    board_id: currentBoardId.value
  });
};

const redo = () => {
  if (!canRedo.value) return;
  socket.value.emit('redo_request', { 
    user_email: userInfo.value.email,
    board_id: currentBoardId.value
  });
};

const handleKeyDown = (event) => {
  if (event.ctrlKey || event.metaKey) {
    if (event.key === 'z') {
      event.preventDefault();
      undo();
    } else if (event.key === 'y') {
      event.preventDefault();
      redo();
    }
  }
};

function switchBoard(board) {
  if (!socket.value || !socket.value.connected) return;

  const boardId = typeof board === 'object' ? board.id : board;
  
  if (currentBoardId.value === boardId) return;

  console.log(`FRONTEND: Trocando para a lousa ${boardId}`);
  
  strokes.value = [];
  redoStack.value = [];
  redraw();

  currentBoardId.value = boardId;
  
  socket.value.emit('join_board', {
    board_id: currentBoardId.value,
    user_email: userInfo.value?.email
  });
}

function handleBoardSelected(board) {
  switchBoard(board);
}

function handleBoardDeleted(deletedBoardId) {
  if (currentBoardId.value === deletedBoardId) {
    console.log(`FRONTEND: A lousa atual (${deletedBoardId}) foi deletada. Voltando para a principal.`);
    switchBoard({ id: 1, nickname: "Lousa Principal" });
  }
}

onMounted(() => {
  setupViewportAndWorld();
  window.addEventListener('resize', setupViewportAndWorld);
  window.addEventListener('keydown', handleKeyDown);

  const backendUrl = import.meta.env.VITE_API_URL || 'https://project3-2025a-gabriel.onrender.com';
  socket.value = io(backendUrl, {
    transports: ['websocket', 'polling']
  });

  socket.value.on('connect', () => {
    console.log('FRONTEND: Conectado ao servidor Socket.IO com ID:', socket.value.id);
    if (userInfo.value?.email) {
      socket.value.emit('join_board', { board_id: currentBoardId.value, user_email: userInfo.value.email });
    }
  });

  socket.value.on('connection_established', (data) => {
    console.log('FRONTEND: ' + data.message, 'SID do servidor:', data.sid);
  });

  socket.value.on('disconnect', () => {
    console.log('FRONTEND: Desconectado do servidor Socket.IO');
  });

  socket.value.on('initial_drawing', (data) => {
    console.log(`FRONTEND: Recebendo desenho inicial para lousa.`, data.strokes.length, 'traços');
    strokes.value = data.strokes.map(strokeData => ({
      id: strokeData.id,
      user_id: strokeData.user_id,
      points: strokeData.points,
      color: strokeData.color,
      lineWidth: strokeData.lineWidth
    }));
    redraw();
  });

  socket.value.on('stroke_received', (strokeData) => {
    if (strokeData.board_id !== currentBoardId.value) return;

    if (strokeData.temp_id && strokeData.user_id === userInfo.value.id) {
      const tempStrokeIndex = strokes.value.findIndex(s => s.id === strokeData.temp_id);
      if (tempStrokeIndex !== -1) {
        strokes.value[tempStrokeIndex] = {
          id: strokeData.id,
          user_id: strokeData.user_id,
          points: strokeData.points,
          color: strokeData.color,
          lineWidth: strokeData.lineWidth,
        };
        redraw();
        return;
      }
    }
    
    if (strokeData.user_id === userInfo.value?.id) {
      if (redoStack.value.length > 0) {
        redoStack.value.pop();
      }
    }
    
    strokes.value.push(strokeData);
    redraw();
  });

  socket.value.on('stroke_removed', (data) => {
    if (data.board_id !== currentBoardId.value) return;
    
    const index = strokes.value.findIndex(s => s.id === data.stroke_id);
    if (index !== -1) {
      const [removedStroke] = strokes.value.splice(index, 1);

      if (removedStroke.user_id === userInfo.value?.id) {
        redoStack.value.push(removedStroke);
      }
      
      redraw();
    }
  });

  socket.value.on('canvas_cleared', (data) => {
    if (data.board_id !== currentBoardId.value) return;

    console.log(`FRONTEND: Evento de limpar canvas recebido do servidor para a lousa ${data.board_id}.`);
    strokes.value = [];
    redoStack.value = [];
    redraw();
  });
});

onUnmounted(() => {
  window.removeEventListener('resize', setupViewportAndWorld);
  window.removeEventListener('keydown', handleKeyDown);
  if (socket.value) {
    socket.value.disconnect();
  }
});

function setupViewportAndWorld() {
  const canvas = viewportCanvasRef.value;
  if (!canvas) return;
  const availableWidth = window.innerWidth;
  const availableHeight = window.innerHeight;
  let newViewportWidth = availableWidth;
  let newViewportHeight = availableWidth / TARGET_VIEWPORT_ASPECT_RATIO;
  if (newViewportHeight > availableHeight) {
    newViewportHeight = availableHeight;
    newViewportWidth = availableHeight * TARGET_VIEWPORT_ASPECT_RATIO;
  }
  viewportState.width = Math.floor(newViewportWidth);
  viewportState.height = Math.floor(newViewportHeight);
  canvas.width = viewportState.width;
  canvas.height = viewportState.height;
  ctx = canvas.getContext('2d');
  if (!ctx) return;
  resetView();
}

function resetView() {
  if (!ctx) return;
  const scaleX = viewportState.width / WORLD_WIDTH;
  const scaleY = viewportState.height / WORLD_HEIGHT;
  viewportState.scale = Math.min(scaleX, scaleY) * 0.9;
  viewportState.offsetX = (viewportState.width - WORLD_WIDTH * viewportState.scale) / 2;
  viewportState.offsetY = (viewportState.height - WORLD_HEIGHT * viewportState.scale) / 2;
  redraw();
}

function redraw() {
  if (!ctx) return;
  const canvas = viewportCanvasRef.value;
  ctx.fillStyle = '#777777'; 
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(viewportState.offsetX, viewportState.offsetY);
  ctx.scale(viewportState.scale, viewportState.scale);
  ctx.fillStyle = WORLD_BACKGROUND_COLOR;
  ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT); 
  ctx.clip(); 
  strokes.value.forEach(stroke => {
    if (stroke.points.length < 2) return;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    ctx.strokeStyle = stroke.color;
    ctx.lineWidth = stroke.lineWidth; 
    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    stroke.points.forEach(point => ctx.lineTo(point.x, point.y));
    ctx.stroke();
  });
  ctx.restore(); 
  ctx.restore(); 
}

function screenToWorldCoordinates(screenX, screenY) {
  return {
    x: (screenX - viewportState.offsetX) / viewportState.scale,
    y: (screenY - viewportState.offsetY) / viewportState.scale,
  };
}

function getCanvasCoordinates(event) {
  const rect = viewportCanvasRef.value.getBoundingClientRect();
  const screenX = event.clientX - rect.left;
  const screenY = event.clientY - rect.top;
  return screenToWorldCoordinates(screenX, screenY);
}

function handleMouseDown(event) {
  menu.visible = false;

  if (event.button === 0) { 
    isDrawing = true;
    
    redoStack.value = [];

    const { x, y } = getCanvasCoordinates(event);
    
    currentTempStrokeId = 'temp_' + Date.now();

    const newStroke = {
      id: currentTempStrokeId,
      user_id: userInfo.value.id,
      points: [{ x, y }],
      color: drawingSettings.color,
      lineWidth: drawingSettings.lineWidth,
      is_temp: true,
    };

    strokes.value.push(newStroke);
    redraw();
  }
  else if (event.button === 1) {
    event.preventDefault();
    viewportState.isPanning = true;
    viewportState.lastPanX = event.clientX;
    viewportState.lastPanY = event.clientY;
  }
}

function handleMouseMove(event) {
  if (isDrawing) {
    const activeStroke = strokes.value.find(s => s.id === currentTempStrokeId);
    if (activeStroke) {
      const { x, y } = getCanvasCoordinates(event);
      activeStroke.points.push({ x, y });
      redraw();
    }
  }
  else if (viewportState.isPanning) {
    const dx = event.clientX - viewportState.lastPanX;
    const dy = event.clientY - viewportState.lastPanY;
    viewportState.offsetX += dx;
    viewportState.offsetY += dy;
    viewportState.lastPanX = event.clientX;
    viewportState.lastPanY = event.clientY;
    redraw();
  }
}

function handleMouseUp(event) {
  if (event.button === 0 && isDrawing) {
    isDrawing = false;
    const finalStroke = strokes.value.find(s => s.id === currentTempStrokeId);

    if (finalStroke && finalStroke.points.length > 1 && socket.value) {
      socket.value.emit('draw_stroke_event', {
        board_id: currentBoardId.value,
        user_email: userInfo.value?.email,
        points: finalStroke.points,
        color: finalStroke.color,
        lineWidth: finalStroke.lineWidth,
        temp_id: finalStroke.id,
      });
    } else if (finalStroke) {
      const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
      if (index !== -1) {
        strokes.value.splice(index, 1);
        redraw();
      }
    }
    currentTempStrokeId = null;
  }
  
  if (event.button === 1) {
    viewportState.isPanning = false;
  }
}

function handleMouseOut(event) {
  if (isDrawing) {
    handleMouseUp({ button: 0 }); 
  }
  if (viewportState.isPanning) {
    viewportState.isPanning = false;
  }
}

function handleWheel(event) {
  event.preventDefault();
  menu.visible = false;
  const scaleAmountFactor = 1.1;
  const mouseX_view = event.offsetX;
  const mouseY_view = event.offsetY;
  const worldP_before = screenToWorldCoordinates(mouseX_view, mouseY_view);
  let newScale = viewportState.scale;
  if (event.deltaY < 0) {
    newScale *= scaleAmountFactor;
  } else {
    newScale /= scaleAmountFactor;
  }
  newScale = Math.max(0.05, Math.min(newScale, 20));
  viewportState.scale = newScale;
  viewportState.offsetX = mouseX_view - worldP_before.x * viewportState.scale;
  viewportState.offsetY = mouseY_view - worldP_before.y * viewportState.scale;
  redraw();
}

function showContextMenuAt(screenX, screenY) {
  if (socket.value) socket.value.emit('debug_touch_event', { type: 'showContextMenuAt_Triggered', screenX, screenY, sid: socket.value.id });
  
  if (currentTempStrokeId) {
    const index = strokes.value.indexOf(strokes.value.find(s => s.id === currentTempStrokeId));
    if (index > -1) {
      strokes.value.splice(index, 1);
      if (socket.value) socket.value.emit('debug_touch_event', { type: 'showContextMenuAt_ClearedSpeculativeStroke', sid: socket.value.id });
    }
    currentTempStrokeId = null;
  }
  isDrawing = false;

  menu.x = screenX;
  menu.y = screenY;
  menu.visible = true;
}

function handleTouchStart(event) {
  event.preventDefault();
  isDrawing = true;
  
  redoStack.value = [];

  const touch = event.touches[0];
  const { x, y } = screenToWorldCoordinates(touch.clientX, touch.clientY);
  
  currentTempStrokeId = 'temp_' + Date.now();

  const newStroke = {
    id: currentTempStrokeId,
    user_id: userInfo.value.id,
    points: [{ x, y }],
    color: drawingSettings.color,
    lineWidth: drawingSettings.lineWidth,
    is_temp: true,
  };
  strokes.value.push(newStroke);
  redraw();
}

function handleTouchMove(event) {
  event.preventDefault();
  if (!isDrawing) return;

  const activeStroke = strokes.value.find(s => s.id === currentTempStrokeId);
  if (activeStroke) {
    const touch = event.touches[0];
    const { x, y } = screenToWorldCoordinates(touch.clientX, touch.clientY);
    activeStroke.points.push({ x, y });
    redraw();
  }
}

function handleTouchEnd(event) {
  event.preventDefault();
  if (!isDrawing) return;
  isDrawing = false;

  const finalStroke = strokes.value.find(s => s.id === currentTempStrokeId);

  if (finalStroke && finalStroke.points.length > 1 && socket.value) {
    socket.value.emit('draw_stroke_event', {
      board_id: currentBoardId.value,
      user_email: userInfo.value.email,
      points: finalStroke.points,
      color: finalStroke.color,
      lineWidth: finalStroke.lineWidth,
      temp_id: finalStroke.id,
    });
  }
  currentTempStrokeId = null;
}

function showContextMenu(event) {
  menu.x = event.clientX;
  menu.y = event.clientY;
  menu.visible = true;
}

function handleMenuSelection(action, value) {
  menu.visible = false;
  switch (action) {
    case 'clear':
      if (confirm('Tem certeza que deseja limpar o canvas para todos?')) {
        console.log(`FRONTEND: Enviando evento para limpar canvas da lousa ${currentBoardId.value}`);
        if (socket.value) {
          socket.value.emit('clear_canvas_event', { board_id: currentBoardId.value });
        }
        strokes.value = [];
        redoStack.value = [];
        redraw();
      }
      break;
    case 'resetView':
      resetView();
      break;
    case 'setColor':
      drawingSettings.color = value;
      break;
    case 'setThickness':
      drawingSettings.lineWidth = value;
      break;
  }
}

function getDistance(p1, p2) {
  // ... existing code ...
}
</script>

<style scoped>
.canvas-ui-container {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 100;
}

.left-controls {
  display: flex;
  align-items: flex-start; /* Alinha os itens no topo */
  gap: 10px;
}

.undo-redo-container {
  display: flex;
  flex-direction: column; /* Organiza os botões verticalmente */
  gap: 8px;
  /* O alinhamento com o WhiteboardMenu já é feito pelo flex-start do container pai */
}

.undo-redo-container button {
  background-color: #ffffff;
  border: 1px solid #dadce0;
  border-radius: 8px; /* Cantos levemente arredondados */
  width: 40px; /* Tamanho ajustado */
  height: 40px;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 1px 3px rgba(60,64,67,0.15);
  color: #3c4043;
  transition: background-color 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.undo-redo-container button:hover:not(:disabled) {
  background-color: #f8f9fa;
  border-color: #d2d5d8;
  box-shadow: 0 1px 4px rgba(60,64,67,0.2);
}

.undo-redo-container button:disabled {
  color: #9e9e9e;
  cursor: not-allowed;
  background-color: #f5f5f5;
  box-shadow: none;
}

.viewport-canvas {
  border: 1px solid #505050;
  background-color: #f0f0f0;
  display: block;
  touch-action: none; /* Previne o scroll do navegador em touch screens */
}
</style>