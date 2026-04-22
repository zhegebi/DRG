import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import DocGen from '../views/DocGen.vue'
import DRG from '../views/DRG.vue'
const routes: Array<RouteRecordRaw> = [
    {
        path:'/',
        redirect:'/home'
    },
    {
        path:'/home',
        name: 'home',
        component: Home
    },
    {
        path:'/DocGen',
        name: 'docgen',
        component: DocGen
    },
    {
        path:'/DRG',
        name: 'drg',
        component: DRG
    }
]

const router = createRouter({
    history: createWebHistory('/'),
    routes
})

export default router