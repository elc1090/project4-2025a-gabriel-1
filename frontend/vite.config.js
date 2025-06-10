import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: '/project3-2025a-gabriel/',
  build: {
    outDir: '../docs'
	}
})
