import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import Home from '../views/Home/Home.vue' 

const routes: Array<RouteRecordRaw> = [
    {
        path: '/',
        name: 'home',
        component: Home
    },
    {
        path: '/DocGen',
        name: 'docgen',
        component: () => import('../views/Doc.vue')
    },
    {
        path: '/DRG',
        name: 'drg',
        component: () => import('../views/DRG.vue')
    }
]

const router = createRouter({
    history: createWebHistory('/'),
    routes
})

export default router