<template>
  <div class="glass-panel p-4">
    <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
      <h3 class="font-bold text-slate-100 flex items-center gap-2 text-base">
        <span>⚙️</span> Parámetros del Sistema
      </h3>
      <button
        @click="saveConfig"
        :disabled="isSaving"
        class="btn btn-start text-xs py-1.5 px-3"
      >
        <span v-if="isSaving">Guardando...</span>
        <span v-else>Guardar Cambios</span>
      </button>
    </div>

    <div class="space-y-4">
      <!-- 1. TIEMPO DE RECONOCIMIENTO (TIEMPO_REQUERIDO) -->
      <div>
        <div class="flex justify-between items-center mb-1">
          <label class="text-xs font-semibold text-slate-300">
            Tiempo de Reconocimiento Continuo (s):
          </label>
          <span class="text-xs font-mono font-bold text-cyan-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            {{ localConfig.recognition_time }} seg
          </span>
        </div>
        <p class="text-[11px] text-slate-400 mb-2">
          Tiempo continuo que YOLO debe detectar el tornillo para ordenar el movimiento al brazo.
        </p>
        <div class="flex items-center gap-3">
          <input
            type="range"
            v-model.number="localConfig.recognition_time"
            min="0.05"
            max="3.0"
            step="0.05"
            class="w-full accent-cyan-500 cursor-pointer"
          />
          <input
            type="number"
            v-model.number="localConfig.recognition_time"
            min="0.05"
            max="10.0"
            step="0.05"
            class="input-field w-24 text-center font-mono text-xs py-1"
          />
        </div>
      </div>

      <!-- 2. ID DE CÁMARA (0, 1, 2...) -->
      <div>
        <div class="flex justify-between items-center mb-1">
          <label class="text-xs font-semibold text-slate-300">
            ID del Dispositivo de Cámara:
          </label>
          <button @click="detectCameras" class="text-[11px] text-cyan-400 hover:underline">
            Escanear cámaras
          </button>
        </div>
        <p class="text-[11px] text-slate-400 mb-2">
          Índice numérico asignado por OpenCV (por ejemplo 0 para integrada, 1 o 2 para USB externa).
        </p>
        <div class="flex items-center gap-2">
          <select v-if="availableCameras.length > 0" v-model.number="localConfig.camera_id" class="input-field text-xs font-mono">
            <option v-for="cam in availableCameras" :key="cam.id" :value="cam.id">
              {{ cam.name }}
            </option>
          </select>
          <input
            v-else
            type="number"
            v-model.number="localConfig.camera_id"
            min="0"
            max="10"
            class="input-field font-mono text-xs"
            placeholder="0, 1 o 2"
          />
          <span class="text-xs text-slate-400 whitespace-nowrap">ID: {{ localConfig.camera_id }}</span>
        </div>
      </div>

      <!-- 3. PUERTO SERIAL (POR DEFECTO /dev/ttyUSB0) -->
      <div>
        <div class="flex justify-between items-center mb-1">
          <label class="text-xs font-semibold text-slate-300">
            Puerto Serie del Microcontrolador:
          </label>
          <button @click="$emit('open-serial-guide')" class="text-[11px] text-amber-400 hover:underline font-semibold flex items-center gap-1">
            <span>ℹ️</span> ¿Cómo ver mi puerto?
          </button>
        </div>
        <p class="text-[11px] text-slate-400 mb-2">
          Puerto asignado en Linux al ESP32 / Arduino (por defecto: <code class="text-cyan-400">/dev/ttyUSB0</code>).
        </p>
        <div class="flex items-center gap-2">
          <input
            type="text"
            v-model="localConfig.serial_port"
            class="input-field font-mono text-xs"
            placeholder="/dev/ttyUSB0"
          />
          <button
            @click="refreshPorts"
            title="Escanear puertos serie conectados"
            class="btn btn-secondary px-3 py-1.5 text-xs whitespace-nowrap"
          >
            Refrescar
          </button>
        </div>

        <!-- Lista rápida de puertos detectados -->
        <div v-if="portsList.length > 0" class="mt-2 flex flex-wrap gap-1">
          <button
            v-for="p in portsList"
            :key="p.device"
            @click="localConfig.serial_port = p.device"
            class="text-[10px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900 text-slate-300 hover:border-cyan-500 font-mono"
            :class="{ 'border-cyan-400 text-cyan-300 font-bold': localConfig.serial_port === p.device }"
          >
            {{ p.device }}
          </button>
        </div>
      </div>

      <!-- 4. UMBRAL DE CONFIANZA YOLO -->
      <div>
        <div class="flex justify-between items-center mb-1">
          <label class="text-xs font-semibold text-slate-300">
            Umbral de Confianza YOLO:
          </label>
          <span class="text-xs font-mono text-slate-400">{{ Math.round(localConfig.confidence * 100) }}%</span>
        </div>
        <input
          type="range"
          v-model.number="localConfig.confidence"
          min="0.2"
          max="0.95"
          step="0.05"
          class="w-full accent-cyan-500 cursor-pointer"
        />
      </div>

      <!-- Ruta del Modelo YOLO -->
      <div class="pt-2 border-t border-slate-800 text-[11px] text-slate-400 font-mono truncate">
        <span class="text-slate-500 block">Modelo cargado:</span>
        <span class="text-slate-300 truncate block" :title="localConfig.model_path">{{ localConfig.model_path }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    required: true
  },
  portsList: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['save-config', 'open-serial-guide', 'refresh-ports'])

const localConfig = ref({ ...props.config })
const isSaving = ref(false)
const availableCameras = ref([])

watch(() => props.config, (newVal) => {
  localConfig.value = { ...newVal }
}, { deep: true })

const saveConfig = async () => {
  isSaving.value = true
  await emit('save-config', localConfig.value)
  isSaving.value = false
}

const refreshPorts = () => {
  emit('refresh-ports')
}

const detectCameras = async () => {
  try {
    const res = await fetch('/api/system/cameras')
    const data = await res.json()
    availableCameras.value = data.cameras || []
  } catch (e) {
    console.error('Error detectando cámaras:', e)
  }
}
</script>
