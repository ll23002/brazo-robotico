<template>
  <div class="glass-panel p-4 flex flex-wrap items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <span class="text-sm font-semibold text-slate-300">Control General:</span>
      <div class="flex items-center gap-2">
        <!-- Botón Iniciar -->
        <button
          @click="$emit('action', 'start')"
          :disabled="status.status === 'RUNNING' || status.status === 'BUSY'"
          class="btn btn-start"
          :class="{ 'glow-green': status.status === 'RUNNING' }"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
          Iniciar
        </button>

        <!-- Botón Pausar -->
        <button
          @click="$emit('action', 'pause')"
          :disabled="status.status === 'PAUSED' || status.status === 'STOPPED'"
          class="btn btn-pause"
          :class="{ 'glow-amber': status.status === 'PAUSED' }"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
          Pausar
        </button>

        <!-- Botón Apagar -->
        <button
          @click="$emit('action', 'stop')"
          :disabled="status.status === 'STOPPED'"
          class="btn btn-stop"
          :class="{ 'glow-red': status.status === 'STOPPED' }"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42A6.92 6.92 0 0 1 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.05.88-3.9 2.29-5.18l-1.42-1.42A8.96 8.96 0 0 0 3 12a9 9 0 0 0 9 9 9 9 0 0 0 9-9c0-2.61-1.12-4.96-3.17-6.83z"/>
          </svg>
          Apagar
        </button>
      </div>
    </div>

    <!-- Indicador de acción actual -->
    <div class="flex items-center gap-2 text-xs text-slate-400">
      <span class="w-2 h-2 rounded-full" :class="status.is_connected_serial ? 'bg-emerald-400' : 'bg-red-400'"></span>
      <span>
        {{ status.is_connected_serial ? 'Brazo sincronizado y listo' : 'Brazo desconectado (revisa puerto serie)' }}
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  status: {
    type: Object,
    required: true
  }
})

defineEmits(['action'])
</script>
