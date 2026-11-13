<template>
  <div class="glass-panel p-4 flex flex-col h-64">
    <div class="flex items-center justify-between mb-2 pb-2 border-b border-slate-800">
      <div class="flex items-center gap-2">
        <span class="text-xs font-mono text-cyan-400">&gt;_</span>
        <h3 class="font-bold text-slate-100 text-sm">
          Terminal de Telemetría y Logs
        </h3>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="autoScroll = !autoScroll"
          class="text-[11px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900"
          :class="autoScroll ? 'text-cyan-400 border-cyan-500' : 'text-slate-400'"
        >
          Auto-scroll: {{ autoScroll ? 'ON' : 'OFF' }}
        </button>
        <button
          @click="$emit('clear')"
          class="text-[11px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900 text-slate-400 hover:text-white"
        >
          Limpiar
        </button>
      </div>
    </div>

    <!-- Contenedor scrollable de mensajes -->
    <div
      ref="logContainer"
      class="flex-1 overflow-y-auto font-mono text-[11px] space-y-1 bg-slate-950/70 p-2.5 rounded border border-slate-900"
    >
      <div v-if="logs.length === 0" class="text-slate-500 italic text-center py-4">
        Esperando eventos del sistema, cámara y brazo robótico...
      </div>
      <div
        v-for="(log, idx) in logs"
        :key="idx"
        class="flex items-start gap-2 leading-relaxed"
      >
        <span class="text-slate-500 select-none">[{{ log.timestamp }}]</span>
        <span
          class="px-1 py-0.2 rounded font-bold text-[10px] uppercase select-none"
          :class="getSourceBadgeClass(log.source)"
        >
          {{ log.source }}
        </span>
        <span class="text-slate-200 flex-1 break-words">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  }
})

defineEmits(['clear'])

const logContainer = ref(null)
const autoScroll = ref(true)

watch(() => props.logs.length, () => {
  if (autoScroll.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
})

const getSourceBadgeClass = (source) => {
  switch (source) {
    case 'YOLO': return 'bg-cyan-950 text-cyan-300 border border-cyan-800'
    case 'ARDUINO': return 'bg-emerald-950 text-emerald-300 border border-emerald-800'
    case 'SERIAL': return 'bg-purple-950 text-purple-300 border border-purple-800'
    case 'SISTEMA': return 'bg-blue-950 text-blue-300 border border-blue-800'
    case 'ARDUINO-CLI': return 'bg-amber-950 text-amber-300 border border-amber-800'
    default: return 'bg-slate-800 text-slate-300'
  }
}
</script>
