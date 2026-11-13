<template>
  <div class="glass-panel p-4">
    <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
      <h3 class="font-bold text-slate-100 flex items-center gap-2 text-base">
        <span>⚡</span> Microcontrolador & Firmware
      </h3>
      <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
        arduino-cli
      </span>
    </div>

    <!-- Sección de Flasheo sin IDE de Arduino -->
    <div class="space-y-3">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
        <div>
          <label class="text-xs font-semibold text-slate-300 block mb-1">
            Placa de Desarrollo:
          </label>
          <select v-model="selectedFqbn" class="input-field text-xs font-mono">
            <option v-for="b in boards" :key="b.fqbn" :value="b.fqbn">
              {{ b.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-300 block mb-1">
            Puerto de Destino:
          </label>
          <input
            type="text"
            v-model="targetPort"
            class="input-field text-xs font-mono"
            placeholder="/dev/ttyUSB0"
          />
        </div>
      </div>

      <!-- Botón de Flasheo -->
      <button
        @click="flashFirmware"
        :disabled="isFlashing"
        class="w-full btn btn-secondary text-xs py-2 flex items-center justify-center gap-2 font-bold hover:border-cyan-500"
      >
        <span v-if="isFlashing" class="animate-spin">⏳</span>
        <span v-else>⚡</span>
        {{ isFlashing ? 'Compilando y Subiendo Firmware...' : 'Compilar y Flashear Sketch (Sin IDE de Arduino)' }}
      </button>

      <!-- Mensaje de resultado de Flasheo -->
      <div v-if="flashResult" class="p-2.5 rounded text-xs font-mono max-h-32 overflow-y-auto" :class="flashResult.success ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800' : 'bg-red-950/80 text-red-300 border border-red-800'">
        <div class="font-bold mb-1">{{ flashResult.success ? '✅ Proceso completado exitosamente' : '❌ Error al flashear' }}</div>
        <pre class="whitespace-pre-wrap text-[11px]">{{ flashResult.output || flashResult.error || flashResult.message }}</pre>
      </div>

      <!-- Sección de Comandos de Prueba Rápida / Calibración -->
      <div class="pt-3 border-t border-slate-800">
        <label class="text-xs font-semibold text-slate-300 block mb-1.5">
          Comandos Manuales (Calibración):
        </label>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
          <button
            @click="sendManualCmd('1')"
            :disabled="!isConnected"
            class="px-2 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-xs text-slate-200"
            title="Posición inicial / Centro"
          >
            1: Reposo / Centro
          </button>
          <button
            @click="sendManualCmd('2')"
            :disabled="!isConnected"
            class="px-2 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-xs text-slate-200"
            title="Bajar garra"
          >
            2: Bajar Garra
          </button>
          <button
            @click="sendManualCmd('4,1')"
            :disabled="!isConnected"
            class="px-2 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-xs text-slate-200"
            title="Rotar a la derecha"
          >
            4,1: Derecha (0°)
          </button>
          <button
            @click="sendManualCmd('4,2')"
            :disabled="!isConnected"
            class="px-2 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-xs text-slate-200"
            title="Rotar a la izquierda"
          >
            4,2: Izquierda (180°)
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  currentPort: {
    type: String,
    default: '/dev/ttyUSB0'
  },
  isConnected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send-cmd'])

const boards = ref([
  { name: 'ESP32 Dev Module (Recomendado)', fqbn: 'esp32:esp32:esp32' },
  { name: 'Arduino Uno', fqbn: 'arduino:avr:uno' },
  { name: 'Arduino Nano', fqbn: 'arduino:avr:nano' }
])
const selectedFqbn = ref('esp32:esp32:esp32')
const targetPort = ref(props.currentPort)
const isFlashing = ref(false)
const flashResult = ref(null)

onMounted(async () => {
  try {
    const res = await fetch('/api/arduino/boards')
    const data = await res.json()
    if (data.boards) {
      boards.value = data.boards
    }
  } catch (e) {
    console.error('Error cargando placas:', e)
  }
})

const flashFirmware = async () => {
  isFlashing.value = true
  flashResult.value = null
  try {
    const res = await fetch('/api/arduino/flash', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fqbn: selectedFqbn.value,
        port: targetPort.value || props.currentPort
      })
    })
    const data = await res.json()
    flashResult.value = data
  } catch (e) {
    flashResult.value = { success: false, error: e.message }
  } finally {
    isFlashing.value = false
  }
}

const sendManualCmd = (cmd) => {
  emit('send-cmd', cmd)
}
</script>
