<template>
  <div class="sidebar-container">
    <button @click="setTool('pencil')" :class="{ 'active-tool': currentTool === 'pencil' }" title="Pincel" class="sidebar-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
    </button>
    <button @click="setTool('eraser')" :class="{ 'active-tool': currentTool === 'eraser' }" title="Borracha" class="sidebar-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 13.5A3.5 3.5 0 0 0 17 10h-2.5a2.5 2.5 0 0 0-5 0H7a3.5 3.5 0 0 0-3.5 3.5V15a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1v-1.5z"></path><path d="M17 10V5a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v5"></path></svg>
    </button>
    
    <hr class="separator" />

    <WhiteboardMenu
      :selected-board-id="currentBoardId"
      @board-selected="handleBoardSelected"
      @board-created="handleBoardSelected"
      @board-deleted="handleBoardDeleted"
    />

    <button @click="undo" :disabled="!canUndo" title="Desfazer (Ctrl+Z)" class="sidebar-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-corner-up-left"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 0 0-4-4H4"></path></svg>
    </button>
    <button @click="redo" :disabled="!canRedo" title="Refazer (Ctrl+Y)" class="sidebar-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-corner-up-right"><polyline points="15 14 20 9 15 4"></polyline><path d="M4 20v-7a4 4 0 0 1 4-4h12"></path></svg>
    </button>
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
import GestureRecognizer from '@2players/dollar1-unistroke-recognizer';

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

const longPressDuration = 500;
let longPressTimer = null;
let touchStartCoords = {};
const longPressMoveThreshold = 10;

let isMultiTouching = false;
let initialGestureInfo = {};
let potentialDrawingStart = false;

const currentTool = ref('pencil');
const eraserSize = 20; // Raio da borracha em pixels do mundo

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

// --- Configuração do Reconhecedor de Formas ---
const recognizer = new GestureRecognizer({ defaultStrokes: false });
let shapeTemplates = {}; // Será preenchido em onMounted

// Função para gerar pontos de um polígono regular (para triângulo, quadrado, estrela)
const createPolygon = (sides, cx, cy, radius) => {
    const points = [];
    const angleStep = (Math.PI * 2) / sides;
    for (let i = 0; i < sides; i++) {
        // O -Math.PI / 2 é para rotacionar e deixar a base do triângulo/quadrado reta
        points.push({
            x: cx + radius * Math.cos(angleStep * i - Math.PI / 2),
            y: cy + radius * Math.sin(angleStep * i - Math.PI / 2),
        });
    }
    return points;
};

// Função para gerar pontos de uma estrela
const createStar = (cx, cy, outerRadius, innerRadius) => {
    const points = [];
    const sides = 5;
    const angleStep = Math.PI / sides;
    for (let i = 0; i < 2 * sides; i++) {
        const radius = i % 2 === 0 ? outerRadius : innerRadius;
        points.push({
            x: cx + radius * Math.cos(angleStep * i - Math.PI / 2),
            y: cy + radius * Math.sin(angleStep * i - Math.PI / 2),
        });
    }
    return points;
}

// --- Fim da Configuração do Reconhecedor ---

onMounted(() => {
  // Define os modelos de formas para o reconhecedor
  const size = 250; // Tamanho padrão para os modelos
  shapeTemplates = {
      circle: createPolygon(32, size/2, size/2, size/2),
      rectangle: [
          {x:0,y:0},{x:size,y:0},{x:size,y:size},{x:0,y:size},{x:0,y:0}
      ],
      triangle: createPolygon(3, size/2, size/2, size/2),
      star: createStar(size/2, size/2, size/2, size/4)
  };
  
  recognizer.add('circle', shapeTemplates.circle);
  recognizer.add('rectangle', shapeTemplates.rectangle);
  recognizer.add('triangle', shapeTemplates.triangle);
  recognizer.add('star', shapeTemplates.star);
  
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
  if (viewportState.isPanning) {
    const dx = event.clientX - viewportState.lastPanX;
    const dy = event.clientY - viewportState.lastPanY;
    viewportState.offsetX += dx;
    viewportState.offsetY += dy;
    viewportState.lastPanX = event.clientX;
    viewportState.lastPanY = event.clientY;
    redraw();
    return;
  }

  if (!isDrawing) return;

  if (currentTool.value === 'pencil') {
    const activeStroke = strokes.value.find(s => s.id === currentTempStrokeId);
    if (activeStroke) {
      const { x, y } = getCanvasCoordinates(event);
      activeStroke.points.push({ x, y });
      redraw();
    }
  } else if (currentTool.value === 'eraser') {
    const { x: cursorX, y: cursorY } = getCanvasCoordinates(event);
    
    // Itera sobre uma cópia para evitar problemas ao modificar o array
    [...strokes.value].forEach(stroke => {
      // Ignora traços temporários
      if (stroke.is_temp) return;

      const isHit = stroke.points.some(point => {
        const distance = Math.hypot(point.x - cursorX, point.y - cursorY);
        return distance < eraserSize / viewportState.scale; // Ajusta o tamanho da borracha com o zoom
      });

      if (isHit) {
        // Remove o traço da UI imediatamente (UI Otimista)
        const index = strokes.value.findIndex(s => s.id === stroke.id);
        if (index !== -1) {
          strokes.value.splice(index, 1);
          redraw();

          // Emite o evento para o servidor deletar permanentemente
          socket.value.emit('erase_stroke', {
            stroke_id: stroke.id,
            board_id: currentBoardId.value
          });
        }
      }
    });
  }
}

function handleMouseUp(event) {
  // Finaliza o desenho com o pincel
  if (event.button === 0 && isDrawing && currentTool.value === 'pencil') {
    isDrawing = false;
    const finalStroke = strokes.value.find(s => s.id === currentTempStrokeId);

    if (!finalStroke) return;

    // Tenta reconhecer a forma antes de finalizar
    if (finalStroke.points.length > 10) { 
        const result = recognizer.recognize(finalStroke.points, true);
        if (result && result.score > 0.75) { // Limiar de confiança um pouco maior
            // Remove o traço desenhado
            const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
            if (index !== -1) {
                strokes.value.splice(index, 1);
            }
            
            // Cria a forma perfeita
            createPerfectShape(result.name, finalStroke);
            redraw();
            currentTempStrokeId = null;
            return;
        }
    }

    // Se não for uma forma reconhecida, finaliza como um traço normal
    if (finalStroke.points.length > 1 && socket.value) {
      socket.value.emit('draw_stroke_event', {
        board_id: currentBoardId.value,
        user_email: userInfo.value?.email,
        points: finalStroke.points,
        color: finalStroke.color,
        lineWidth: finalStroke.lineWidth,
        temp_id: finalStroke.id,
      });
    } else {
      // Se for apenas um clique, remove o traço temporário
      const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
      if (index !== -1) {
          strokes.value.splice(index, 1);
          redraw();
      }
    }
    
    currentTempStrokeId = null; // Limpa o ID temporário
  }
  
  // Finaliza a ação da borracha
  if (event.button === 0 && isDrawing && currentTool.value === 'eraser') {
    isDrawing = false;
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
  menu.visible = false;
  const touches = event.touches;
  
  if (touches.length === 1) {
    isMultiTouching = false;
    potentialDrawingStart = true;
    const touch = touches[0];
    touchStartCoords = { x: touch.clientX, y: touch.clientY, time: Date.now() };

    clearTimeout(longPressTimer);
    longPressTimer = setTimeout(() => {
      if (potentialDrawingStart && !isMultiTouching) {
        showContextMenuAt(touchStartCoords.x, touchStartCoords.y);
      }
      longPressTimer = null;
    }, longPressDuration);

  } else if (touches.length >= 2) {
    clearTimeout(longPressTimer);
    longPressTimer = null;
    potentialDrawingStart = false;
    isDrawing = false;
    
    if (currentTempStrokeId) {
        const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
        if (index !== -1) strokes.value.splice(index, 1);
        currentTempStrokeId = null;
        redraw();
    }
    
    isMultiTouching = true;
    const t1 = touches[0];
    const t2 = touches[1];
    initialGestureInfo.pinchDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
    
    const rect = viewportCanvasRef.value.getBoundingClientRect();
    const screenMidX = (t1.clientX - rect.left + t2.clientX - rect.left) / 2;
    const screenMidY = (t1.clientY - rect.top + t2.clientY - rect.top) / 2;
    
    initialGestureInfo.worldMidpoint = screenToWorldCoordinates(screenMidX, screenMidY);
  }
}

function handleTouchMove(event) {
  event.preventDefault();
  const touches = event.touches;
  
  if (touches.length === 1 && !isMultiTouching) {
    const touch = touches[0];
    
    if (potentialDrawingStart) {
      const deltaX = touch.clientX - touchStartCoords.x;
      const deltaY = touch.clientY - touchStartCoords.y;

      if (Math.hypot(deltaX, deltaY) > longPressMoveThreshold) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
        
        if (!isDrawing) {
           isDrawing = true;
           potentialDrawingStart = false;
           
           redoStack.value = [];
           const { x, y } = getCanvasCoordinates(touch);
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
      }
    }
    
    if (isDrawing) {
      if (currentTool.value === 'pencil') {
        const activeStroke = strokes.value.find(s => s.id === currentTempStrokeId);
        if (activeStroke) {
          const { x, y } = getCanvasCoordinates(touch);
          activeStroke.points.push({ x, y });
          redraw();
        }
      } else if (currentTool.value === 'eraser') {
        const { x: cursorX, y: cursorY } = getCanvasCoordinates(touch);
        [...strokes.value].forEach(stroke => {
          if (stroke.is_temp) return;
          const isHit = stroke.points.some(point => {
            const distance = Math.hypot(point.x - cursorX, point.y - cursorY);
            return distance < eraserSize / viewportState.scale;
          });
          if (isHit) {
            const index = strokes.value.findIndex(s => s.id === stroke.id);
            if (index !== -1) {
              strokes.value.splice(index, 1);
              redraw();
              socket.value.emit('erase_stroke', {
                stroke_id: stroke.id,
                board_id: currentBoardId.value
              });
            }
          }
        });
      }
    }
  } else if (touches.length >= 2 && isMultiTouching) {
    const t1 = touches[0];
    const t2 = touches[1];
    
    const rect = viewportCanvasRef.value.getBoundingClientRect();
    const currentScreenMidX = (t1.clientX - rect.left + t2.clientX - rect.left) / 2;
    const currentScreenMidY = (t1.clientY - rect.top + t2.clientY - rect.top) / 2;
    
    viewportState.offsetX = currentScreenMidX - initialGestureInfo.worldMidpoint.x * viewportState.scale;
    viewportState.offsetY = currentScreenMidY - initialGestureInfo.worldMidpoint.y * viewportState.scale;

    const currentPinchDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
    let scaleFactor = 1;
    if (initialGestureInfo.pinchDistance > 0) {
      scaleFactor = currentPinchDistance / initialGestureInfo.pinchDistance;
    }
    let newScale = viewportState.scale * scaleFactor;
    newScale = Math.max(0.1, Math.min(newScale, 20));
    
    viewportState.offsetX += (initialGestureInfo.worldMidpoint.x * viewportState.scale) - (initialGestureInfo.worldMidpoint.x * newScale);
    viewportState.offsetY += (initialGestureInfo.worldMidpoint.y * viewportState.scale) - (initialGestureInfo.worldMidpoint.y * newScale);
    viewportState.scale = newScale;

    initialGestureInfo.pinchDistance = currentPinchDistance;
    initialGestureInfo.worldMidpoint = screenToWorldCoordinates(currentScreenMidX, currentScreenMidY);

    redraw();
  }
}

function handleTouchEnd(event) {
  event.preventDefault();
  clearTimeout(longPressTimer);

  if (isDrawing) {
    const finalStroke = strokes.value.find(s => s.id === currentTempStrokeId);
    
    if (!finalStroke) {
        isDrawing = false;
        potentialDrawingStart = false;
        currentTempStrokeId = null;
        return;
    }

    // Tenta reconhecer a forma
    if (finalStroke.points.length > 10) {
        const result = recognizer.recognize(finalStroke.points, true);
        if (result && result.score > 0.75) {
            const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
            if (index !== -1) {
                strokes.value.splice(index, 1);
            }
            createPerfectShape(result.name, finalStroke);
            redraw();
        } else {
            // Se não for forma, envia como traço normal
            if (finalStroke.points.length > 1 && socket.value) {
                socket.value.emit('draw_stroke_event', {
                    board_id: currentBoardId.value,
                    user_email: userInfo.value?.email,
                    points: finalStroke.points,
                    color: finalStroke.color,
                    lineWidth: finalStroke.lineWidth,
                    temp_id: finalStroke.id,
                });
            } else {
                const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
                if (index !== -1) strokes.value.splice(index, 1);
                redraw();
            }
        }
    } else {
        // Se não tiver pontos suficientes para reconhecimento, trata como traço normal
        if (finalStroke.points.length > 1 && socket.value) {
            socket.value.emit('draw_stroke_event', {
                board_id: currentBoardId.value,
                user_email: userInfo.value?.email,
                points: finalStroke.points,
                color: finalStroke.color,
                lineWidth: finalStroke.lineWidth,
                temp_id: finalStroke.id,
            });
        } else {
            const index = strokes.value.findIndex(s => s.id === currentTempStrokeId);
            if (index !== -1) strokes.value.splice(index, 1);
            redraw();
        }
    }
  }
  
  // Limpa o estado para o próximo toque
  isDrawing = false;
  isMultiTouching = false;
  potentialDrawingStart = false;
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

const setTool = (tool) => {
  currentTool.value = tool;
};

// Função que cria e emite a forma perfeita
const createPerfectShape = (shapeName, originalStroke) => {
    // Encontra o centro e o tamanho (bounding box) do desenho original
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    originalStroke.points.forEach(p => {
        minX = Math.min(minX, p.x);
        minY = Math.min(minY, p.y);
        maxX = Math.max(maxX, p.x);
        maxY = Math.max(maxY, p.y);
    });

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const width = maxX - minX;
    const height = maxY - minY;
    const radius = Math.max(width, height) / 2;

    let perfectPoints = [];
    switch (shapeName) {
        case 'circle':
            perfectPoints = createPolygon(32, cx, cy, radius); // Círculo com 32 lados
            break;
        case 'rectangle':
            perfectPoints = [
                { x: minX, y: minY }, { x: maxX, y: minY },
                { x: maxX, y: maxY }, { x: minY, y: maxY },
                { x: minX, y: minY } // Fecha o retângulo
            ];
            break;
        case 'triangle':
            perfectPoints = createPolygon(3, cx, cy, radius);
            perfectPoints.push(perfectPoints[0]); // Fecha o triângulo
            break;
        case 'star':
            perfectPoints = createStar(cx, cy, radius, radius / 2.5);
            perfectPoints.push(perfectPoints[0]); // Fecha a estrela
            break;
    }

    if (perfectPoints.length > 0) {
        const newStrokeId = 'temp_' + Date.now();
        const perfectStroke = {
            id: newStrokeId,
            user_id: userInfo.value.id,
            points: perfectPoints,
            color: originalStroke.color,
            lineWidth: originalStroke.lineWidth,
        };

        strokes.value.push(perfectStroke);

        socket.value.emit('draw_stroke_event', {
            board_id: currentBoardId.value,
            user_email: userInfo.value?.email,
            points: perfectStroke.points,
            color: perfectStroke.color,
            lineWidth: perfectStroke.lineWidth,
            temp_id: newStrokeId,
        });
    }
};
</script>

<style scoped>
.sidebar-container {
  position: absolute;
  top: 50%;
  left: 16px;
  transform: translateY(-50%);
  z-index: 100;
  
  background-color: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 12px;
  
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.separator {
  width: 100%;
  border: none;
  border-top: 1px solid #e8eaed;
  margin: 0;
}

/* Estilo para os botões da sidebar, incluindo o do componente WhiteboardMenu */
:deep(.whiteboard-menu-button),
.sidebar-button {
  background-color: transparent;
  border: none;
  border-radius: 12px;
  width: 48px;
  height: 48px;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #5f6368;
  transition: background-color 0.2s;
  padding: 0;
}

:deep(.whiteboard-menu-button:hover:not(:disabled)),
.sidebar-button:hover:not(:disabled) {
  background-color: #f1f3f4;
}

.sidebar-button.active-tool {
  background-color: #e8f0fe; /* Um azul claro para indicar seleção */
  color: #1967d2; /* Um azul mais escuro para o ícone */
}

.sidebar-button:disabled {
  color: #bdc1c6;
  cursor: not-allowed;
}

.viewport-canvas {
  border: 1px solid #505050;
  background-color: #f0f0f0;
  display: block;
  touch-action: none; /* Previne o scroll do navegador em touch screens */
}
</style>