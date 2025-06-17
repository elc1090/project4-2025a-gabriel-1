<template>
  <div class="canvas-container">
    <canvas
      ref="viewportCanvasRef"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUpOrOut"
      @mouseout="handleMouseUpOrOut"
      @wheel.prevent="handleWheel"
      @touchstart.prevent="handleTouchStart"
      @touchmove.prevent="handleTouchMove"
      @touchend="handleTouchEnd"
      @contextmenu.prevent="showContextMenu"
      class="viewport-canvas"
    ></canvas>
    <ContextMenu
      v-if="menu.visible"
      :x="menu.x"
      :y="menu.y"
      @select="handleMenuSelection"
    />
    <button @click="toggleMenu" class="menu-button">☰</button>
    <div v-if="isMenuOpen" class="placeholder-menu">
      <!-- O conteúdo do menu virá aqui -->
      <p>Menu Placeholder</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import ContextMenu from './ContextMenu.vue';
import { io } from 'socket.io-client';

const socket = ref(null);

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
let currentStroke = null;
let isDrawing = false; // Adicionado para controlar o estado de desenho
let potentialDrawingStart = false;

const drawingSettings = reactive({
  color: 'black',
  lineWidth: 3,
});

const isMenuOpen = ref(false);

const menu = reactive({
  visible: false,
  x: 0,
  y: 0,
});

const longPressDuration = 700; // ms para o toque longo (ajustei um pouco)
let longPressTimer = null;
let touchStartCoords = { x: 0, y: 0, time: 0 };
const longPressMoveThreshold = 10; // Pixels

let isMultiTouching = false;
let initialGestureInfo = {
  pinchDistance: 0,
  midpoint: { x: 0, y: 0 },
  worldMidpoint: { x: 0, y: 0},
  offsetX: 0,
  offsetY: 0,
  scale: 1,
};

// --- Ciclo de Vida e Conexão Socket.IO ---
onMounted(() => {
  setupViewportAndWorld();
  window.addEventListener('resize', setupViewportAndWorld);

  const backendUrl = 'https://project3-2025a-gabriel.onrender.com';
  socket.value = io(backendUrl, {
    transports: ['websocket', 'polling']
  });

  socket.value.on('connect', () => {
    console.log('FRONTEND: Conectado ao servidor Socket.IO com ID:', socket.value.id);
  });

  socket.value.on('connection_established', (data) => {
    console.log('FRONTEND: ' + data.message, 'SID do servidor:', data.sid);
  });

  socket.value.on('disconnect', () => {
    console.log('FRONTEND: Desconectado do servidor Socket.IO');
  });

  socket.value.on('initial_drawing', (data) => {
    console.log('FRONTEND: Recebendo desenho inicial:', data.strokes.length, 'traços');
    strokes.value = data.strokes.map(strokeData => ({
      points: strokeData.points,
      color: strokeData.color,
      lineWidth: strokeData.lineWidth
    }));
    redraw();
  });

  socket.value.on('stroke_received', (strokeData) => {
    console.log('FRONTEND: Novo traço recebido:', strokeData);
    strokes.value.push({
      points: strokeData.points,
      color: strokeData.color,
      lineWidth: strokeData.lineWidth
    });
    redraw();
  });

  socket.value.on('canvas_cleared', () => {
    console.log('FRONTEND: Evento de limpar canvas recebido do servidor.');
    strokes.value = [];
    redraw();
  });
});

onUnmounted(() => {
  window.removeEventListener('resize', setupViewportAndWorld);
  if (socket.value) {
    socket.value.disconnect();
  }
});

// --- Funções de Setup, Desenho e Coordenadas (sem alterações nas lógicas centrais) ---
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

// --- Manipuladores de Eventos de Mouse (mantidos como na sua versão) ---
function handleMouseDown(event) {
  menu.visible = false;
  isDrawing = false; // Resetar isDrawing para interações de mouse
  if (event.button === 0) {
    const { x, y } = screenToWorldCoordinates(event.offsetX, event.offsetY);
    currentStroke = {
      points: [{ x, y }],
      color: drawingSettings.color,
      lineWidth: drawingSettings.lineWidth,
    };
    strokes.value.push(currentStroke);
    isDrawing = true; // Mouse está desenhando
    redraw(); // Para mostrar o primeiro ponto do mouse
  } else if (event.button === 1) {
    event.preventDefault();
    viewportState.isPanning = true;
    viewportState.lastPanX = event.clientX;
    viewportState.lastPanY = event.clientY;
  }
}

function handleMouseMove(event) {
  if (isDrawing && currentStroke && (event.buttons & 1)) { // Verifica se o botão esquerdo está pressionado
    const { x, y } = screenToWorldCoordinates(event.offsetX, event.offsetY);
    currentStroke.points.push({ x, y });
    redraw();
  } else if (viewportState.isPanning && (event.buttons & 4)) {
    const dx = event.clientX - viewportState.lastPanX;
    const dy = event.clientY - viewportState.lastPanY;
    viewportState.offsetX += dx;
    viewportState.offsetY += dy;
    viewportState.lastPanX = event.clientX;
    viewportState.lastPanY = event.clientY;
    redraw();
  }
}

function handleMouseUpOrOut(event) {
  if (event.button === 0 && currentStroke) { // Se estava desenhando com o botão esquerdo
    if (currentStroke.points.length > 1 && socket.value) {
      socket.value.emit('draw_stroke_event', {
        points: currentStroke.points,
        color: currentStroke.color,
        lineWidth: currentStroke.lineWidth
      });
    } else if (currentStroke.points.length <= 1) { // Remove ponto único se não arrastou
        const index = strokes.value.indexOf(currentStroke);
        if (index > -1) strokes.value.splice(index,1);
        redraw();
    }
    isDrawing = false;
  }
  currentStroke = null; // Resetar sempre, independente do botão

  if (event.button === 1 || !(event.buttons & 4)) {
    viewportState.isPanning = false;
  }
}

function handleWheel(event) {
  event.preventDefault();
  menu.visible = false; // Opcional: fechar menu no zoom
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

// --- Manipuladores de Toque ATUALIZADOS COM DEPURAÇÃO DETALHADA ---

function showContextMenuAt(screenX, screenY) {
  if (socket.value) socket.value.emit('debug_touch_event', { type: 'showContextMenuAt_Triggered', screenX, screenY, sid: socket.value.id });
  
  potentialDrawingStart = false;

  if (currentStroke) {
    const index = strokes.value.indexOf(currentStroke);
    if (index > -1) {
      strokes.value.splice(index, 1);
      if (socket.value) socket.value.emit('debug_touch_event', { type: 'showContextMenuAt_ClearedSpeculativeStroke', sid: socket.value.id });
    }
    currentStroke = null;
  }
  isDrawing = false;

  menu.x = screenX;
  menu.y = screenY;
  menu.visible = true;
}

function handleTouchStart(event) {
  event.preventDefault();
  const touches = event.touches;
  const rect = viewportCanvasRef.value.getBoundingClientRect();
  
  if (socket.value) {
    const touchDataForDebug = Array.from(touches).map(t => ({ id: t.identifier, clientX: t.clientX, clientY: t.clientY }));
    socket.value.emit('debug_touch_event', {
      type: 'touchstart_ENTRY',
      touchesLength: touches.length,
      userAgent: navigator.userAgent,
      touchData: touchDataForDebug,
      sid: socket.value.id
    });
  }

  menu.visible = false;
  
  if (touches.length === 1) {
    isMultiTouching = false;
    isDrawing = false;
    currentStroke = null;
    potentialDrawingStart = true;

    const touch = touches[0];
    touchStartCoords = { x: touch.clientX, y: touch.clientY, time: Date.now() };

    clearTimeout(longPressTimer);
    longPressTimer = setTimeout(() => {
      if (potentialDrawingStart && !isMultiTouching) { // Só dispara se ainda for um candidato a toque longo
        if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchstart_LongPress_TimerFired_Successfully', sid: socket.value.id });
        showContextMenuAt(touchStartCoords.x, touchStartCoords.y);
        // showContextMenuAt já define potentialDrawingStart = false e isDrawing = false
      } else {
        if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchstart_LongPress_TimerFired_But_Invalidated', potentialDrawingStart, isMultiTouching, sid: socket.value.id });
      }
      longPressTimer = null;
    }, longPressDuration);

    if (socket.value) {
      socket.value.emit('debug_touch_event', {
        type: 'touchstart_SingleTouch_PotentialStartSet',
        coords: { x: touch.clientX, y: touch.clientY },
        potentialDrawingStart_state: potentialDrawingStart,
        sid: socket.value.id
      });
    }
  
  } else if (touches.length >= 2) {
    if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchstart_MultiTouch_Initiated', sid: socket.value.id, touches: touches.length });
    
    clearTimeout(longPressTimer);
    longPressTimer = null;
    potentialDrawingStart = false; // Não é mais um candidato a desenho de um dedo

    if (isDrawing && currentStroke) {
        if (currentStroke.points.length > 1 && socket.value) {
            socket.value.emit('draw_stroke_event', { points: currentStroke.points, color: currentStroke.color, lineWidth: currentStroke.lineWidth });
        } else if(currentStroke) {
            const index = strokes.value.indexOf(currentStroke);
            if (index > -1) strokes.value.splice(index, 1);
        }
    }
    isDrawing = false; 
    currentStroke = null;
    isMultiTouching = true;

    const t1 = touches[0];
    const t2 = touches[1];
    initialGestureInfo.pinchDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
    const screenMidX = (t1.clientX - rect.left + t2.clientX - rect.left) / 2;
    const screenMidY = (t1.clientY - rect.top + t2.clientY - rect.top) / 2;
    initialGestureInfo.midpoint = { x: screenMidX, y: screenMidY };
    initialGestureInfo.worldMidpoint = screenToWorldCoordinates(screenMidX, screenMidY);
    initialGestureInfo.offsetX = viewportState.offsetX;
    initialGestureInfo.offsetY = viewportState.offsetY;
    initialGestureInfo.scale = viewportState.scale;
    redraw();
  }
}

function handleTouchMove(event) {
  event.preventDefault();
  const touches = event.touches;
  const rect = viewportCanvasRef.value.getBoundingClientRect();

  if (socket.value && touches.length > 0) {
    const touchDataForDebug = Array.from(touches).map(t => ({ id: t.identifier, clientX: t.clientX, clientY: t.clientY }));
    socket.value.emit('debug_touch_event', {
      type: 'touchmove_ENTRY',
      touchesLength: touches.length,
      isDrawing_state: isDrawing,
      isMultiTouching_state: isMultiTouching,
      currentStroke_exists: !!currentStroke,
      longPressTimer_active: !!longPressTimer,
      potentialDrawingStart_state: potentialDrawingStart,
      sid: socket.value.id,
      touchData: touchDataForDebug
    });
  }

  if (touches.length === 1 && !isMultiTouching) {
    const touch = touches[0];
    const screenX = touch.clientX - rect.left;
    const screenY = touch.clientY - rect.top;

    if (potentialDrawingStart) { // Se era um candidato a desenho/toque longo
      const deltaX = touch.clientX - touchStartCoords.x;
      const deltaY = touch.clientY - touchStartCoords.y;

      if (Math.hypot(deltaX, deltaY) > longPressMoveThreshold) {
        // Moveu o suficiente: é um desenho, cancela o toque longo.
        if (longPressTimer) {
          if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchmove_SingleTouch_LongPressCancelledByMove', sid: socket.value.id });
          clearTimeout(longPressTimer);
          longPressTimer = null;
        }
        
        if (!isDrawing) { // Se o desenho ainda não começou oficialmente
          isDrawing = true; // Começa a desenhar AGORA
          potentialDrawingStart = false; // Não é mais "potencial"
          
          // Usa as coordenadas INICIAIS do toque para o primeiro ponto do traço
          const initialWorldCoords = screenToWorldCoordinates(touchStartCoords.x - rect.left, touchStartCoords.y - rect.top);
          currentStroke = {
            points: [initialWorldCoords],
            color: drawingSettings.color,
            lineWidth: drawingSettings.lineWidth,
          };
          strokes.value.push(currentStroke);
          if (socket.value) {
            socket.value.emit('debug_touch_event', {
              type: 'touchmove_SingleTouch_DrawingActuallyStarted',
              isDrawing_state: isDrawing,
              worldX: initialWorldCoords.x, worldY: initialWorldCoords.y,
              sid: socket.value.id
            });
          }
          // Adiciona o ponto ATUAL também, já que houve movimento
          const currentWorldCoords = screenToWorldCoordinates(screenX, screenY);
          currentStroke.points.push(currentWorldCoords);
          redraw();
        }
      }
    }
    
    // Se o desenho já começou (isDrawing é true)
    if (isDrawing && currentStroke) {
      // Só adiciona o ponto se não for o primeiro ponto já adicionado ao iniciar o desenho no move
      // ou se a lógica acima já não adicionou o ponto atual.
      // Para simplificar: se isDrawing e currentStroke, adiciona o ponto atual.
      // A lógica de não duplicar o primeiro ponto pode ser refinada se necessário.
      const worldCoords = screenToWorldCoordinates(screenX, screenY);
      // Evitar pontos duplicados se o movimento for mínimo e já adicionado
      const lastPoint = currentStroke.points[currentStroke.points.length -1];
      if (!lastPoint || lastPoint.x !== worldCoords.x || lastPoint.y !== worldCoords.y) {
          currentStroke.points.push(worldCoords);
      }

      if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchmove_SingleTouch_PointAddedToStroke', points: currentStroke.points.length, sid: socket.value.id });
      redraw();
    } else if (touches.length === 1 && !isDrawing && !potentialDrawingStart && socket.value ) {
        // Caso onde moveu, mas não está desenhando e não é um potencial começo (ex: menu já abriu)
        socket.value.emit('debug_touch_event', { type: 'touchmove_SingleTouch_MoveIgnored_NotDrawingNotPotential', sid: socket.value.id });
    }

  } else if (touches.length >= 2 && isMultiTouching) {
    if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchmove_MultiTouch_Processing', sid: socket.value.id, touches: touches.length });
    
    clearTimeout(longPressTimer); // Garante que o toque longo é cancelado
    longPressTimer = null;
    potentialDrawingStart = false; // Não é um início de desenho de um dedo
    isDrawing = false; // Não está desenhando

    // ... (sua lógica de pan/zoom com initialGestureInfo como antes) ...
    const t1 = touches[0];
    const t2 = touches[1];
    const currentScreenMidX = (t1.clientX - rect.left + t2.clientX - rect.left) / 2;
    const currentScreenMidY = (t1.clientY - rect.top + t2.clientY - rect.top) / 2;
    const currentPinchDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
    let scaleFactor = 1;
    if (initialGestureInfo.pinchDistance > 0) {
      scaleFactor = currentPinchDistance / initialGestureInfo.pinchDistance;
    }
    let newScale = initialGestureInfo.scale * scaleFactor;
    newScale = Math.max(0.05, Math.min(newScale, 20));
    viewportState.scale = newScale;
    viewportState.offsetX = currentScreenMidX - initialGestureInfo.worldMidpoint.x * newScale;
    viewportState.offsetY = currentScreenMidY - initialGestureInfo.worldMidpoint.y * newScale;
    redraw();
  }
}

function handleTouchEnd(event) {
  event.preventDefault();
  const changedTouches = event.changedTouches; // Dedos que foram levantados
  const touchesStillOnScreen = event.touches.length; // Dedos que ainda estão na tela

  if (socket.value) {
    const changedTouchData = Array.from(changedTouches).map(t => ({ id: t.identifier, clientX: t.clientX, clientY: t.clientY }));
    socket.value.emit('debug_touch_event', {
      type: 'touchend_ENTRY',
      touchesOnScreen: touchesStillOnScreen,
      changedTouches: changedTouches.length,
      changedTouchData: changedTouchData,
      isDrawing_state: isDrawing,
      isMultiTouching_state: isMultiTouching,
      currentStroke_exists: !!currentStroke,
      potentialDrawingStart_state: potentialDrawingStart,
      sid: socket.value.id
    });
  }

  clearTimeout(longPressTimer); // Sempre limpa o timer de toque longo
  longPressTimer = null;

  // Verifica se um dedo foi levantado e se era um toque de desenho (não multi-touch)
  if (isDrawing && currentStroke && !isMultiTouching && changedTouches.length > 0) {
    // Assumimos que o changedTouch é o que estava desenhando
    if (currentStroke.points.length > 1) {
      if (socket.value) {
        socket.value.emit('draw_stroke_event', {
          points: currentStroke.points,
          color: currentStroke.color,
          lineWidth: currentStroke.lineWidth
        });
        if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchend_EmittedDrawEvent', points: currentStroke.points.length, sid: socket.value.id });
      }
    } else if (currentStroke) { // Era um toque curto (tap) que não virou desenho
      const index = strokes.value.indexOf(currentStroke);
      if (index > -1) {
        strokes.value.splice(index, 1);
      }
      if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchend_RemovedSingleDotStroke_TapEnd', sid: socket.value.id });
      redraw(); 
    }
  }
  
  potentialDrawingStart = false; // Resetar para o próximo toque

  // Atualiza estados com base nos dedos restantes
  if (touchesStillOnScreen < 2) {
    if (isMultiTouching && socket.value) socket.value.emit('debug_touch_event', { type: 'touchend_Reset_isMultiTouching_to_false', sid: socket.value.id });
    isMultiTouching = false;
  }
  if (touchesStillOnScreen < 1) {
    if (isDrawing && socket.value) socket.value.emit('debug_touch_event', { type: 'touchend_Reset_isDrawing_to_false', sid: socket.value.id });
    isDrawing = false;
    currentStroke = null;
  } else if (touchesStillOnScreen === 1 && isMultiTouching) {
      // Se estava em multi-touch e sobrou um dedo, não necessariamente começa a desenhar.
      // O próximo touchstart desse dedo decidirá. Resetamos isMultiTouching.
      // isDrawing já deve ser false.
  }
}


// --- Funções do Menu de Contexto (mantidas como na sua versão) ---
function showContextMenu(event) {
  menu.x = event.clientX;
  menu.y = event.clientY;
  menu.visible = true;
}

function clearStrokes() { // Renomeada para consistência, chamada pelo menu
  strokes.value = [];
  redraw();
  if (socket.value) { // Notificar o servidor sobre a limpeza
    socket.value.emit('clear_canvas_event', {});
  }
}

function handleMenuSelection(action, value) {
  menu.visible = false;
  switch (action) {
    case 'clear':
      clearStrokes(); // Chama a função de limpeza
      break;
    case 'setColor':
      drawingSettings.color = value;
      break;
    case 'setThickness':
      drawingSettings.lineWidth = value;
      break;
    case 'resetView':
      resetView();
      break;
  }
}

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value;
}
</script>

<style scoped>
.canvas-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #333; /* Cor de fundo para o container */
}

.viewport-canvas {
  /* O canvas já é redimensionado via JS, então não precisa de w/h aqui */
  border: 2px solid #444;
  box-shadow: 0 0 10px rgba(0,0,0,0.5);
  cursor: crosshair;
  display: block;
  touch-action: none;
}

.menu-button {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 100; /* Mais alto para garantir que fique sobre tudo */
  padding: 8px 12px;
  font-size: 24px; /* Maior para ser mais fácil de tocar */
  line-height: 1;
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
  border: 1px solid #ccc;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  transition: background-color 0.2s, box-shadow 0.2s;
  -webkit-tap-highlight-color: transparent; /* Remove o destaque de toque em mobile */
}

.menu-button:hover, .menu-button:focus {
  background-color: #fff;
  box-shadow: 0 4px 8px rgba(0,0,0,0.3);
  outline: none;
}

.placeholder-menu {
  position: absolute;
  top: 70px; /* Abaixo do botão do menu */
  left: 20px;
  z-index: 100;
  width: 250px;
  padding: 15px;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.placeholder-menu p {
  margin: 0;
  font-size: 16px;
  color: #555;
}
</style>