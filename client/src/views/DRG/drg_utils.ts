import {
    createTaskApiDrgTaskCreatePost,
    getTaskListApiDrgTaskListGet,
    getTaskStatusApiDrgTaskStatusGet,
    getTaskResultApiDrgTaskResultTaskIdGet,
    getTaskProgressApiDrgTaskTaskIdProgressStepGet,
} from "@/api";

import type { TaskStep } from "@/api";
import { useAuthStore } from "@/stores/auth";


export const createTask = async (user_input: string, should_generate_test: boolean) => {
    const { data: task_id, error } = await createTaskApiDrgTaskCreatePost({
        body: {
            user_input,
            should_generate_test,
        },
    })
    if (error) {
        throw error
    }
    return task_id
}

export const getTaskList = async () => {
    const { data: task_list, error } = await getTaskListApiDrgTaskListGet()
    if (error) {
        throw error
    }
    return task_list
}

export const getTaskStatus = async (...task_ids: string[]) => {
    const { data: status_list, error } = await getTaskStatusApiDrgTaskStatusGet({
        query: {
            task_ids,
        },
    })
    if (error) {
        throw error
    }
    return status_list
}

export const getTaskResultStream = async (
    task_id: string,
    onChunk: (chunk: string) => void,
): Promise<string> => {
    const authStore = useAuthStore()
    const token = authStore.accessToken

    const response = await fetch(`/api/drg/task/result/${task_id}/stream`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    })

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
        throw new Error("Response body is not readable")
    }

    const decoder = new TextDecoder()
    let fullText = ""

    while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split("\n")

        for (const line of lines) {
            if (line.startsWith("data: ")) {
                const chunk = line.slice(6)
                if (chunk === "[END]") {
                    return fullText
                }
                fullText += chunk
                onChunk(chunk)
            }
        }
    }

    return fullText
}

export const getTaskResult = async (task_id: string) => {
    const { data: result, error } = await getTaskResultApiDrgTaskResultTaskIdGet({
        path: {
            task_id,
        },
    })
    if (error) {
        throw error
    }
    return result
}

export const getTaskProgress = async (task_id: string, step: TaskStep) => {
    const { data: progress, error } = await getTaskProgressApiDrgTaskTaskIdProgressStepGet({
        path: {
            task_id,
            step,
        },
    })
    if (error) {
        throw error
    }
    return progress
}