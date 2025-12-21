/**
 * 进行中任务状态管理
 * 
 * 独立管理当前正在执行的研究任务状态
 * 与 research.ts（报告数据）完全解耦
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface LogEntry {
    time: string
    level: 'info' | 'success' | 'warning' | 'error'
    message: string
}

export interface TaskStats {
    notesFound: number
    contentsAnalyzed: number
    insightsExtracted: number
}

export const useActiveTaskStore = defineStore('activeTask', () => {
    // 当前任务主题
    const topic = ref('')

    // 是否正在运行
    const isRunning = ref(false)

    // 当前阶段
    const stage = ref('')

    // 已完成阶段
    const completedStages = ref<string[]>([])

    // 任务开始时间戳（毫秒）
    const startTime = ref<number>(0)

    // 任务完成时保存的最终耗时（秒）
    const finalElapsedTime = ref<number>(0)

    // 用于触发UI更新的tick（每秒更新一次）
    const tick = ref(0)

    // 任务日志
    const logs = ref<LogEntry[]>([])

    // 统计数据
    const stats = ref<TaskStats>({
        notesFound: 0,
        contentsAnalyzed: 0,
        insightsExtracted: 0
    })

    // 计算耗时（秒）- 基于开始时间戳，依赖tick触发更新
    const elapsedTime = computed(() => {
        // 访问 tick.value 来触发响应式更新
        tick.value
        // 如果有保存的最终耗时（任务已完成），返回它
        if (finalElapsedTime.value > 0) return finalElapsedTime.value
        // 如果任务正在运行，计算实时耗时
        if (!startTime.value || !isRunning.value) return 0
        return Math.floor((Date.now() - startTime.value) / 1000)
    })

    // 更新tick（触发elapsedTime重新计算）
    const updateTick = () => {
        tick.value++
    }

    // 开始任务
    const startTask = (taskTopic: string) => {
        topic.value = taskTopic
        isRunning.value = true
        stage.value = 'planning'
        completedStages.value = []
        startTime.value = Date.now()  // 记录开始时间戳
        finalElapsedTime.value = 0  // 清空之前的最终耗时
        tick.value = 0
        logs.value = []
        stats.value = { notesFound: 0, contentsAnalyzed: 0, insightsExtracted: 0 }
    }

    // 更新阶段
    const setStage = (newStage: string) => {
        if (stage.value && !completedStages.value.includes(stage.value)) {
            completedStages.value.push(stage.value)
        }
        stage.value = newStage
    }

    // 添加日志
    const addLog = (level: LogEntry['level'], message: string) => {
        const now = new Date()
        logs.value.push({
            time: now.toLocaleTimeString('zh-CN', { hour12: false }),
            level,
            message
        })
    }

    // 更新统计
    const updateStats = (newStats: Partial<TaskStats>) => {
        stats.value = { ...stats.value, ...newStats }
    }

    // 标记任务完成（保留日志和统计数据，供用户查看）
    const markCompleted = () => {
        // 保存最终耗时
        if (startTime.value) {
            finalElapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
        }
        isRunning.value = false
        // 保留 topic, logs, stats, completedStages, finalElapsedTime 等数据
    }

    // 清空任务（用户进入编辑页面后调用）
    const clearTask = () => {
        topic.value = ''
        isRunning.value = false
        stage.value = ''
        completedStages.value = []
        startTime.value = 0
        finalElapsedTime.value = 0
        tick.value = 0
        logs.value = []
        stats.value = { notesFound: 0, contentsAnalyzed: 0, insightsExtracted: 0 }
    }

    // 是否有进行中的任务（正在运行）
    const hasActiveTask = computed(() => isRunning.value && topic.value !== '')

    // 是否有已完成的任务（等待用户确认）
    const hasCompletedTask = computed(() => !isRunning.value && topic.value !== '' && logs.value.length > 0)

    return {
        // State
        topic,
        isRunning,
        stage,
        completedStages,
        startTime,
        logs,
        stats,

        // Getters (computed)
        elapsedTime,
        hasActiveTask,
        hasCompletedTask,

        // Actions
        startTask,
        setStage,
        addLog,
        updateStats,
        updateTick,
        markCompleted,
        clearTask
    }
})
