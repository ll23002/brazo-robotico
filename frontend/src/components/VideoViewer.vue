<template>
  <div class="glass-panel p-4 flex flex-col h-full">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full" :class="statusDotClass"></div>
        <h2 class="font-bold text-lg text-slate-100 flex items-center gap-2">
          Visión en Vivo (Cámara {{ config.camera_id }})
        </h2>
      </div>

      <div class="flex items-center gap-3">
        <span class="text-xs font-mono px-2 py-1 bg-slate-900 border border-slate-750 rounded text-cyan-400">
          FPS: {{ status.fps }}
        </span>
        <span :class="badgeClass" class="badge">
          {{ statusText }}
        </span>
      </div>
    </div>

    <!-- Contenedor del Stream de Video -->
    <div class="relative bg-slate-950 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center min-h-[380px] shadow-inner">
      <img
        :src="videoUrl"
        alt="Video Stream YOLO"
        class="w-full h-auto object-contain max-h-[500px]"
        @error="onImageError"
      />

      <!-- Overlay si el sistema está detenido o desconectado -->
      <div v-if="imgError" class="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center p-6 text-center">
        <div class="w-12 h-12 mb-3 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center font-bold text-xl">!</div>
        <p class="text-slate-200 font-semibold mb-1">Sin señal del stream</p>
        <p class="text-xs text-slate-400 mb-4 max-w-sm">
          Verifica que el backend esté ejecutándose y que la cámara ID {{ config.camera_id }} esté conectada.
        </p>
        <button @click="reloadStream" class="btn btn-secondary text-sm">
          Reintentar conexión
        </button>
      </div>

      <!-- Banner flotante cuando el brazo está en movimiento -->
      <div v-if="status.status === 'BUSY'" class="absolute top-4 left-4 right-4 bg-amber-500/90 text-slate-950 font-bold px-4 py-2 rounded shadow-lg flex items-center justify-between text-sm animate-pulse">
        <span>🤖 BRAZO EN MOVIMIENTO (Recolección en progreso...)</span>
        <span class="text-xs">Visión temporalmente suspendida</span>
      </div>

      <!-- Barra de persistencia en tiempo real en la UI -->
      <div v-if="status.persistence_progress > 0" class="absolute bottom-4 left-4 right-4 bg-slate-900/90 border border-slate-700 p-3 rounded-lg backdrop-blur">
        <div class="flex justify-between items-center text-xs mb-1 font-semibold">
          <span class="text-cyan-400">Detectado: {{ status.last_detected_object }}</span>
          <span class="text-slate-300">{{ Math.round(status.persistence_progress * 100) }}%</span>
        </div>
        <div class="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-75"
            :style="{ width: `${status.persistence_progress * 100}%` }"
          ></div>
        </div>
        <div class="text-[10px] text-slate-400 mt-1 flex justify-between">
          <span>Validando estabilidad en escena...</span>
          <span>Umbral: {{ config.recognition_time }}s</span>
        </div>
      </div>
    </div>

    <!-- Resumen de detección inferior -->
    <div class="grid grid-cols-3 gap-3 mt-3 text-xs">
      <div class="bg-slate-900/80 p-2.5 rounded border border-slate-800">
        <span class="text-slate-400 block text-[11px]">Última Detección:</span>
        <span class="font-bold text-slate-200">{{ status.last_detected_object }}</span>
      </div>
      <div class="bg-slate-900/80 p-2.5 rounded border border-slate-800">
        <span class="text-slate-400 block text-[11px]">Conexión Brazo:</span>
        <span :class="status.is_connected_serial ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'">
          {{ status.is_connected_serial ? 'Conectado (' + config.serial_port + ')' : 'Desconectado' }}
        </span>
      </div>
      <div class="bg-slate-900/80 p-2.5 rounded border border-slate-800">
        <span class="text-slate-400 block text-[11px]">Tiempo Validación:</span>
        <span class="font-bold text-cyan-400">{{ config.recognition_time }} seg</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  status: {
    type: Object,
    required: true
  },
  config: {
    type: Object,
    required: true
  }
})

const imgError = ref(false)
const streamKey = ref(Date.now())

const videoUrl = computed(() => {
  return `/api/video/stream?t=${streamKey.value}`
})

const reloadStream = () => {
  imgError.value = false
  streamKey.value = Date.now()
}

const onImageError = () => {
  imgError.value = true
}

const statusText = computed(() => {
  switch (props.status.status) {
    case 'RUNNING': return 'Activo'
    case 'PAUSED': return 'Pausado'
    case 'BUSY': return 'Ocupado'
    case 'STOPPED': return 'Apagado'
    default: return props.status.status
  }
})

const badgeClass = computed(() => {
  switch (props.status.status) {
    case 'RUNNING': return 'badge-running'
    case 'PAUSED': return 'badge-paused'
    case 'BUSY': return 'badge-busy'
    case 'STOPPED': return 'badge-stopped'
    default: return 'badge-stopped'
  }
})

const statusDotClass = computed(() => {
  switch (props.status.status) {
    case 'RUNNING': return 'bg-emerald-500 animate-ping'
    case 'PAUSED': return 'bg-blue-500'
    case 'BUSY': return 'bg-amber-500 animate-pulse'
    case 'STOPPED': return 'bg-red-500'
    default: return 'bg-slate-500'
  }
})
</script>
