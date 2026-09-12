import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// 多模式构建：默认（production）输出 dist 全量应用；
// vite build --mode search|media|control|review 输出 dist-<mode> 子包。
// dev server 不动：dev 默认全量，vite --mode media 可调试子包。
export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        // 本地调试时用 VITE_DEV_API_TARGET 覆盖（如 http://localhost:8081）
        target: process.env.VITE_DEV_API_TARGET || 'http://backend:8081',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: mode === 'production' ? 'dist' : `dist-${mode}`,
    emptyOutDir: true,
  },
}));
