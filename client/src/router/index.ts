import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
const routes: Array<RouteRecordRaw> = [
    {
        path: '/',
        name: 'home',
        component: () => import('../views/Home.vue')
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