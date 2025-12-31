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
        },
        {
            path: '/compare',
            name: 'compare',
            component: () => import('../views/CompareView.vue')
        },
        // 发布相关路由
        {
            path: '/publish/edit/:draftId?',
            name: 'publish-edit',
            component: () => import('../views/PublishEditView.vue')
        },
        {
            path: '/publish/preview/:draftId',
            name: 'publish-preview',
            component: () => import('../views/PublishPreviewView.vue')
        },
        {
            path: '/publish/result/:draftId',
            name: 'publish-result',
            component: () => import('../views/PublishResultView.vue')
        }
    ]
})

export default router

