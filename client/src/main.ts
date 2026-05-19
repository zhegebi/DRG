import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { client } from '@/api/client.gen'

const app = createApp(App)

client.setConfig({
  auth: () => localStorage.getItem('access_token') ?? undefined,
})

app.use(createPinia()) 
app.use(router)

app.mount('#app')