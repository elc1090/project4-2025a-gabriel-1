<template>
  <div class="whiteboard-menu-container">
    <button @click="toggleMenu" class="menu-toggle-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
    </button>
    <div v-if="isMenuOpen" class="menu-content" @click.stop>
      <div class="menu-header">
        <div class="user-info">
          <img :src="userInfo?.profile_pic" alt="Avatar" class="user-avatar">
          <div class="user-details">
            <span class="user-name">{{ userInfo?.name }}</span>
            <span class="user-id">{{ userInfo?.id }}</span>
          </div>
        </div>
        <button @click="closeMenu" class="close-btn">&times;</button>
      </div>
      <h3 class="boards-title">Minhas Lousas</h3>
      <ul>
        <li v-for="board in boards" :key="board.id" @click="selectBoard(board)" :class="{ active: board.id === selectedBoardId }">
          <span>{{ board.nickname }}</span>
          <button v-if="board.is_owner" @click.stop="deleteBoard(board.id)" class="delete-board-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </button>
        </li>
      </ul>
      <div v-if="!userInfo?.is_guest" class="menu-footer">
        <input v-model="newBoardName" placeholder="Apelido da nova lousa" @keyup.enter="createBoard"/>
        <button @click="createBoard" :disabled="!newBoardName.trim()">+ Criar Lousa</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { userInfo } from '../services/userInfo';

const props = defineProps({
  selectedBoardId: Number
});

const emit = defineEmits(['board-selected', 'board-created', 'board-deleted']);

const isMenuOpen = ref(false);
const boards = ref([]);
const newBoardName = ref('');
const API_URL = import.meta.env.VITE_API_URL || 'https://project3-2025a-gabriel.onrender.com';

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value;
  if (isMenuOpen.value) {
    fetchBoards();
  }
};

const closeMenu = () => {
  isMenuOpen.value = false;
};

const fetchBoards = async () => {
  if (!userInfo.value?.email) {
    console.error("Menu: Usuário não logado.");
    return;
  }
  try {
    const response = await fetch(`${API_URL}/api/whiteboards?email=${encodeURIComponent(userInfo.value.email)}`);
    if (!response.ok) throw new Error('Falha ao buscar lousas');
    boards.value = await response.json();
  } catch (error) {
    console.error("Erro ao buscar lousas:", error);
    // TODO: Mostrar erro para o usuário
  }
};

const createBoard = async () => {
  if (!newBoardName.value.trim() || !userInfo.value?.email) return;

  try {
    const response = await fetch(`${API_URL}/api/whiteboards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nickname: newBoardName.value.trim(),
        email: userInfo.value.email,
      }),
    });
    if (!response.ok) throw new Error('Falha ao criar lousa');
    const newBoard = (await response.json()).whiteboard;
    newBoardName.value = '';
    fetchBoards(); // Atualiza a lista
    emit('board-created', newBoard);
    selectBoard(newBoard); // Seleciona a nova lousa
  } catch (error) {
    console.error("Erro ao criar lousa:", error);
  }
};

const deleteBoard = async (boardId) => {
  if (!userInfo.value?.email) return;
  if (boardId === 1) {
    alert("Não é possível deletar a lousa principal.");
    return;
  }
  if (!confirm("Tem certeza que deseja deletar esta lousa? Esta ação não pode ser desfeita.")) {
    return;
  }

  try {
    const response = await fetch(`${API_URL}/api/whiteboards/${boardId}?email=${encodeURIComponent(userInfo.value.email)}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Falha ao deletar lousa');
    }
    fetchBoards();
    emit('board-deleted', boardId);
  } catch (error) {
    console.error("Erro ao deletar lousa:", error);
    alert(`Erro: ${error.message}`);
  }
};

const selectBoard = (board) => {
  emit('board-selected', board);
  closeMenu();
};

onMounted(() => {
  // O menu só busca as lousas quando aberto, mas podemos querer buscar na montagem
  // se o menu estiver visível por padrão em algumas visualizações.
});

// Se o usuário mudar (login/logout), podemos querer recarregar as lousas
watch(userInfo, (newUserInfo) => {
  if (isMenuOpen.value && newUserInfo?.email) {
    fetchBoards();
  } else if (!newUserInfo?.email) {
    boards.value = [];
    isMenuOpen.value = false;
  }
}, { deep: true });

</script>

<style scoped>
.whiteboard-menu-container {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 100;
}

.menu-toggle-btn {
  background-color: #fff;
  border: 1px solid #ccc;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
.menu-toggle-btn:hover {
  background-color: #f5f5f5;
}

.menu-content {
  position: absolute;
  top: 50px;
  left: 0;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  width: 280px;
  max-height: calc(100vh - 70px);
  display: flex;
  flex-direction: column;
}

.menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-grow: 1;
  overflow: hidden;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
}

.user-details {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.user-name {
  font-weight: bold;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-id {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.boards-title {
  padding: 12px 16px 4px 16px;
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.menu-content ul {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  overflow-y: auto;
}

.menu-content li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
}
.menu-content li:hover {
  background-color: #f5f5f5;
}
.menu-content li.active {
  background-color: #e8f0fe;
  font-weight: bold;
}

.delete-board-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #888;
  padding: 2px;
  display: none;
}
.menu-content li:hover .delete-board-btn {
  display: block; /* Mostra o botão no hover do item da lista */
}
.delete-board-btn:hover {
  color: #d9534f;
}

.menu-footer {
  padding: 12px 16px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 8px;
}
.menu-footer input {
  flex-grow: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.menu-footer button {
  padding: 8px 12px;
  border: none;
  background-color: #4285f4;
  color: white;
  border-radius: 4px;
  cursor: pointer;
}
.menu-footer button:hover {
  background-color: #357ae8;
}
.menu-footer button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style> 