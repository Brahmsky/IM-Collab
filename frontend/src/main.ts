import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useTaskStore } from './stores/taskStore'
import { useSessionStore } from './stores/sessionStore'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

const taskStore = useTaskStore()
const sessionStore = useSessionStore()
taskStore.fetchTasks()
sessionStore.loadOpenGroups()

app.mount('#app')
