<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
    <!-- Navbar / Header -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20">
            🤖
          </div>
          <div>
            <h1 class="font-bold text-lg leading-tight tracking-tight text-white flex items-center gap-2">
              Control Mano Robótica <span class="text-xs font-mono font-normal text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800">YOLO + Arduino</span>
            </h1>
            <p class="text-[11px] text-slate-400">
              Plataforma Unificada de Visión Artificial y Automatización
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <!-- Botón de Sonido ON/OFF -->
          <button
            @click="toggleSound"
            class="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border border-slate-750 bg-slate-900 hover:bg-slate-800 transition"
            :class="soundEnabled ? 'text-cyan-400 border-cyan-600' : 'text-slate-400 border-slate-800'"
            title="Activar o silenciar reproducción de tono.mp3 en el navegador"
          >
            <span>{{ soundEnabled ? '🔊' : '🔇' }}</span>
            <span class="font-semibold">{{ soundEnabled ? 'Tono: ON' : 'Tono: OFF' }}</span>
          </button>

          <!-- Indicador de conexión serial -->
          <div class="flex items-center gap-2 text-xs bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800">
            <span class="w-2.5 h-2.5 rounded-full" :class="status.is_connected_serial ? 'bg-emerald-400' : 'bg-red-400'"></span>
            <span class="font-mono text-slate-300">
              {{ config.serial_port }}
            </span>
          </div>

          <!-- Indicador de cámara -->
          <div class="flex items-center gap-2 text-xs bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800">
            <span class="w-2.5 h-2.5 rounded-full" :class="status.is_camera_active ? 'bg-emerald-400' : 'bg-amber-400'"></span>
            <span class="text-slate-300">
              Cámara {{ config.camera_id }}
            </span>
          </div>
        </div>
      </div>
    </header>

    <!-- Contenido Principal -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-5">
      <!-- 1. Barra de Control Principal (Iniciar, Pausar, Apagar) -->
      <ControlBar
        :status="status"
        @action="handleControlAction"
      />

      <!-- 2. Grid de Video y Ajustes -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <!-- Columna Izquierda: Video Viewer (7 cols) -->
        <div class="lg:col-span-7">
          <VideoViewer
            :status="status"
            :config="config"
          />
        </div>

        <!-- Columna Derecha: Parámetros y Arduino (5 cols) -->
        <div class="lg:col-span-5 space-y-5">
          <!-- Panel de Parámetros Dinámicos -->
          <ConfigPanel
            :config="config"
            :ports-list="portsList"
            @save-config="handleSaveConfig"
            @open-serial-guide="isGuideOpen = true"
            @refresh-ports="fetchPorts"
          />

          <!-- Módulo de Arduino / Flasheo sin IDE -->
          <ArduinoManager
            :current-port="config.serial_port"
            :is-connected="status.is_connected_serial"
            @send-cmd="handleManualCmd"
          />
        </div>
      </div>

      <!-- 3. Consola de Logs y Telemetría -->
      <ConsoleLogs
        :logs="logs"
        @clear="logs = []"
      />
    </main>

    <!-- Modal de Guía de Puertos en Linux -->
    <SerialGuideModal
      :is-open="isGuideOpen"
      :detected-ports="portsList"
      @close="isGuideOpen = false"
      @select-port="onSelectPortFromGuide"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import VideoViewer from './components/VideoViewer.vue'
import ControlBar from './components/ControlBar.vue'
import ConfigPanel from './components/ConfigPanel.vue'
import ArduinoManager from './components/ArduinoManager.vue'
import ConsoleLogs from './components/ConsoleLogs.vue'
import SerialGuideModal from './components/SerialGuideModal.vue'

const status = ref({
  status: 'STOPPED',
  is_connected_serial: false,
  is_camera_active: false,
  last_detected_object: 'Ninguno',
  detected_class_id: -1,
  persistence_progress: 0.0,
  fps: 0.0
})

const config = ref({
  camera_id: 2,
  serial_port: '/dev/ttyUSB0',
  baud_rate: 115200,
  recognition_time: 0.2,
  confidence: 0.6,
  model_path: ''
})

const portsList = ref([])
const logs = ref([])
const isGuideOpen = ref(false)
const soundEnabled = ref(true)

let pollTimer = null
let toneAudio = null

const initAudio = () => {
  if (!toneAudio) {
    toneAudio = new Audio('/tono.mp3')
    toneAudio.preload = 'auto'
  }
}

const playTone = () => {
  if (!soundEnabled.value) return
  initAudio()
  try {
    toneAudio.currentTime = 0
    toneAudio.play().catch(e => {
      console.warn('Audio en navegador en espera de interacción:', e)
    })
  } catch (err) {
    console.warn('Error reproduciendo audio:', err)
  }
}

const toggleSound = () => {
  soundEnabled.value = !soundEnabled.value
  if (soundEnabled.value) {
    playTone()
  }
}

// Reproducir tono automáticamente cuando el brazo pasa a estar ocupado moviéndose
watch(() => status.value.status, (newStatus, oldStatus) => {
  if (newStatus === 'BUSY' && oldStatus !== 'BUSY') {
    playTone()
  }
})

const fetchStatus = async () => {
  try {
    const res = await fetch('/api/status')
    if (res.ok) {
      status.value = await res.json()
    }
  } catch (e) {
    // Backend puede estar iniciando
  }
}

const fetchConfig = async () => {
  try {
    const res = await fetch('/api/config')
    if (res.ok) {
      config.value = await res.json()
    }
  } catch (e) {
    console.error('Error obteniendo config:', e)
  }
}

const fetchPorts = async () => {
  try {
    const res = await fetch('/api/system/ports')
    if (res.ok) {
      const data = await res.json()
      portsList.value = data.ports || []
    }
  } catch (e) {
    console.error('Error obteniendo puertos:', e)
  }
}

const fetchLogs = async () => {
  try {
    const res = await fetch('/api/logs')
    if (res.ok) {
      const data = await res.json()
      logs.value = data.logs || []
    }
  } catch (e) {
    console.error('Error obteniendo logs:', e)
  }
}

const handleControlAction = async (action) => {
  initAudio()
  try {
    const res = await fetch(`/api/control/${action}`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      status.value.status = data.status
      await fetchLogs()
    }
  } catch (e) {
    console.error(`Error enviando acción ${action}:`, e)
  }
}

const handleSaveConfig = async (newCfg) => {
  try {
    const res = await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newCfg)
    })
    if (res.ok) {
      const data = await res.json()
      config.value = data.config
      await fetchLogs()
    }
  } catch (e) {
    console.error('Error guardando configuración:', e)
  }
}

const handleManualCmd = async (cmd) => {
  initAudio()
  if (cmd in { '2': 1, '4,1': 1, '4,2': 1 }) {
    playTone()
  }
  try {
    await fetch('/api/robot/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    })
    await fetchLogs()
  } catch (e) {
    console.error('Error enviando comando manual:', e)
  }
}

const onSelectPortFromGuide = (device) => {
  config.value.serial_port = device
  handleSaveConfig({ serial_port: device })
  isGuideOpen.value = false
}

onMounted(async () => {
  initAudio()
  await fetchConfig()
  await fetchStatus()
  await fetchPorts()
  await fetchLogs()

  // Polling de telemetría y logs cada 600ms
  pollTimer = setInterval(async () => {
    await fetchStatus()
    await fetchLogs()
  }, 600)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
