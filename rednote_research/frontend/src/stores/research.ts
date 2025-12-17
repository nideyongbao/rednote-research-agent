/**
 * 研究状态管理
 * 
 * 管理研究流程中的数据：大纲、笔记、报告等
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface OutlineSection {
    id: string
    title: string
    content: string
    type: 'cover' | 'content' | 'summary'
    images: string[]
}

export interface ResearchNote {
    id: string
    title: string
    content: string
    author: string
    likes: number
    images: string[]
    url: string
}

export interface ResearchReport {
    topic: string
    summary: string
    keyFindings: string[]
    sections: OutlineSection[]
    notes: ResearchNote[]
    createdAt: string
}

export const useResearchStore = defineStore('research', () => {
    // 当前研究主题
    const topic = ref('')

    // 大纲数据
    const outline = ref<OutlineSection[]>([])

    // 收集的笔记
    const notes = ref<ResearchNote[]>([])

    // 研究摘要
    const summary = ref('')

    // 关键发现
    const keyFindings = ref<string[]>([])

    // 是否完成
    const isCompleted = ref(false)

    // 生成唯一 ID
    const generateId = () => `section_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // 设置主题
    const setTopic = (newTopic: string) => {
        topic.value = newTopic
    }

    // 设置大纲
    const setOutline = (sections: OutlineSection[]) => {
        outline.value = sections
    }

    // 添加大纲章节
    const addSection = (type: OutlineSection['type'], content: string = '') => {
        outline.value.push({
            id: generateId(),
            title: '',
            content,
            type,
            images: []
        })
    }

    // 更新章节
    const updateSection = (id: string, updates: Partial<OutlineSection>) => {
        const section = outline.value.find(s => s.id === id)
        if (section) {
            Object.assign(section, updates)
        }
    }

    // 删除章节
    const deleteSection = (id: string) => {
        const index = outline.value.findIndex(s => s.id === id)
        if (index > -1) {
            outline.value.splice(index, 1)
        }
    }

    // 移动章节（拖拽排序）
    const moveSection = (fromIndex: number, toIndex: number) => {
        if (fromIndex === toIndex) return
        const [item] = outline.value.splice(fromIndex, 1)
        outline.value.splice(toIndex, 0, item)
    }

    // 设置笔记
    const setNotes = (newNotes: ResearchNote[]) => {
        notes.value = newNotes
    }

    // 设置摘要
    const setSummary = (newSummary: string) => {
        summary.value = newSummary
    }

    // 设置关键发现
    const setKeyFindings = (findings: string[]) => {
        keyFindings.value = findings
    }

    // 标记完成
    const markCompleted = () => {
        isCompleted.value = true
    }

    // 重置
    const reset = () => {
        topic.value = ''
        outline.value = []
        notes.value = []
        summary.value = ''
        keyFindings.value = []
        isCompleted.value = false
    }

    // 获取报告数据
    const getReport = computed<ResearchReport>(() => ({
        topic: topic.value,
        summary: summary.value,
        keyFindings: keyFindings.value,
        sections: outline.value,
        notes: notes.value,
        createdAt: new Date().toISOString()
    }))

    // 从 JSON 加载
    const loadFromJSON = (data: any) => {
        if (data.topic) topic.value = data.topic
        if (data.outline) outline.value = data.outline
        if (data.notes) notes.value = data.notes
        if (data.summary) summary.value = data.summary
        if (data.keyFindings) keyFindings.value = data.keyFindings
        if (data.isCompleted) isCompleted.value = data.isCompleted
    }

    return {
        // State
        topic,
        outline,
        notes,
        summary,
        keyFindings,
        isCompleted,

        // Actions
        setTopic,
        setOutline,
        addSection,
        updateSection,
        deleteSection,
        moveSection,
        setNotes,
        setSummary,
        setKeyFindings,
        markCompleted,
        reset,
        loadFromJSON,

        // Getters
        getReport
    }
})
