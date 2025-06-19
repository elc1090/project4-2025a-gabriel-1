<template>
  <WhiteboardMenu
    :selected-board-id="currentBoardId"
    @board-selected="handleBoardSelected"
    @board-created="handleBoardSelected"
    @board-deleted="handleBoardDeleted"
  />
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
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
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
let currentStroke = null;
let isDrawing = false;
let potentialDrawingStart = false;

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

function switchBoard(board) {
  if (!socket.value || !socket.value.connected) return;

  const boardId = typeof board === 'object' ? board.id : board;
  
  if (currentBoardId.value === boardId) return;

  console.log(`FRONTEND: Trocando para a lousa ${boardId}`);
  
  strokes.value = [];
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
      points: strokeData.points,
      color: strokeData.color,
      lineWidth: strokeData.lineWidth
    }));
    redraw();
  });

  socket.value.on('stroke_received', (strokeData) => {
    if (strokeData.board_id !== currentBoardId.value) return;

    console.log('FRONTEND: Novo traço recebido:', strokeData);
    strokes.value.push({
      points: strokeData.points,
      color: strokeData.color,
      lineWidth: strokeData.lineWidth
    });
    redraw();
  });

  socket.value.on('canvas_cleared', (data) => {
    if (data.board_id !== currentBoardId.value) return;

    console.log(`FRONTEND: Evento de limpar canvas recebido do servidor para a lousa ${data.board_id}.`);
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

function handleMouseDown(event) {
  menu.visible = false;
  isDrawing = false;
  if (event.button === 0) {
    const { x, y } = screenToWorldCoordinates(event.offsetX, event.offsetY);
    currentStroke = {
      points: [{ x, y }],
      color: drawingSettings.color,
      lineWidth: drawingSettings.lineWidth,
    };
    strokes.value.push(currentStroke);
    isDrawing = true;
    redraw();
  } else if (event.button === 1) {
    event.preventDefault();
    viewportState.isPanning = true;
    viewportState.lastPanX = event.clientX;
    viewportState.lastPanY = event.clientY;
  }
}

function handleMouseMove(event) {
  if (isDrawing && currentStroke && (event.buttons & 1)) {
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
  if (event.button === 0 && currentStroke) {
    if (currentStroke.points.length > 1 && socket.value) {
      socket.value.emit('draw_stroke_event', {
        board_id: currentBoardId.value,
        points: currentStroke.points,
        color: currentStroke.color,
        lineWidth: currentStroke.lineWidth
      });
    } else if (currentStroke.points.length <= 1) {
        const index = strokes.value.indexOf(currentStroke);
        if (index > -1) strokes.value.splice(index,1);
        redraw();
    }
    isDrawing = false;
  }
  currentStroke = null;

  if (event.button === 1 || !(event.buttons & 4)) {
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
      if (potentialDrawingStart && !isMultiTouching) {
        if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchstart_LongPress_TimerFired_Successfully', sid: socket.value.id });
        showContextMenuAt(touchStartCoords.x, touchStartCoords.y);
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
    potentialDrawingStart = false;

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

    if (potentialDrawingStart) {
      const deltaX = touch.clientX - touchStartCoords.x;
      const deltaY = touch.clientY - touchStartCoords.y;

      if (Math.hypot(deltaX, deltaY) > longPressMoveThreshold) {
        if (longPressTimer) {
          if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchmove_SingleTouch_LongPressCancelledByMove', sid: socket.value.id });
          clearTimeout(longPressTimer);
          longPressTimer = null;
        }
        
        if (!isDrawing) {
          isDrawing = true;
          potentialDrawingStart = false;
          
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
          const currentWorldCoords = screenToWorldCoordinates(screenX, screenY);
          currentStroke.points.push(currentWorldCoords);
          redraw();
        }
      }
    }
    
    if (isDrawing && currentStroke) {
      const worldCoords = screenToWorldCoordinates(screenX, screenY);
      const lastPoint = currentStroke.points[currentStroke.points.length -1];
      if (!lastPoint || lastPoint.x !== worldCoords.x || lastPoint.y !== worldCoords.y) {
          currentStroke.points.push(worldCoords);
      }

      if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchmove_SingleTouch_PointAddedToStroke', points: currentStroke.points.length, sid: socket.value.id });
      redraw();
    } else if (touches.length === 1 && !isDrawing && !potentialDrawingStart && socket.value ) {
        socket.value.emit('debug_touch_event', { type: 'touchmove_SingleTouch_MoveIgnored_NotDrawingNotPotential', sid: socket.value.id });
    }

  } else if (touches.length >= 2 && isMultiTouching) {
    if (socket.value) socket.value.emit('debug_touch_event', { type: 'touchmove_MultiTouch_Processing', sid: socket.value.id, touches: touches.length });
    
    clearTimeout(longPressTimer);
    longPressTimer = null;
    potentialDrawingStart = false;
    isDrawing = false;

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
  if (isMultiTouching) {
    isMultiTouching = false;
    return;
  }
  clearTimeout(longPressTimer);

  if (isDrawing && currentStroke) {
    if (currentStroke.points.length > 1 && socket.value) {
        socket.value.emit('draw_stroke_event', {
        board_id: currentBoardId.value,
          points: currentStroke.points,
          color: currentStroke.color,
          lineWidth: currentStroke.lineWidth
        });
    } else if (currentStroke.points.length <= 1) {
      const index = strokes.value.indexOf(currentStroke);
      if (index > -1) {
        strokes.value.splice(index, 1);
      }
      redraw(); 
    }
  }
  
    isDrawing = false;
    currentStroke = null;
  potentialDrawingStart = false;
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
.viewport-canvas {
  border: 1px solid #505050;
  cursor: crosshair;
  background-color: #777;
  display: block;
  touch-action: none;
  box-shadow: 0 0 10px rgba(0,0,0,0.3);
  margin: auto;
}
</style>