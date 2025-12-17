import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ResearchView from '../views/ResearchView.vue'
import OutlineView from '../views/OutlineView.vue'
import ReportView from '../views/ReportView.vue'
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'home',
            component: HomeView
        },
        {
            path: '/research',
            name: 'research',
            component: ResearchView
        },
        {
            path: '/outline',
            name: 'outline',
            component: OutlineView
        },
        {
            path: '/report',
            name: 'report',
            component: ReportView
        },
        {
            path: '/history',
            name: 'history',
            component: HistoryView
        },
        {
            path: '/history/:id',
            name: 'history-detail',
            component: HistoryView
        },
        {
            path: '/settings',
            name: 'settings',
            component: SettingsView
        }
    ]
})

export default router
