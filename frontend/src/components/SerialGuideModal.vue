<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
    <div class="glass-panel w-full max-w-xl p-6 relative bg-slate-900 border-slate-700 shadow-2xl">
      <!-- Botón de Cerrar -->
      <button
        @click="$emit('close')"
        class="absolute top-4 right-4 text-slate-400 hover:text-white text-xl font-bold p-1 leading-none"
      >
        ✕
      </button>

      <div class="flex items-center gap-2 mb-4">
        <span class="text-2xl">🔌</span>
        <h3 class="text-lg font-bold text-slate-100">
          Guía: ¿Cómo identificar el puerto serie en Linux?
        </h3>
      </div>

      <p class="text-sm text-slate-300 mb-4">
        Cuando conectas tu microcontrolador (ESP32 o Arduino) por USB en Linux, el sistema le asigna un archivo de dispositivo en <code class="bg-slate-950 px-1 py-0.5 rounded text-cyan-400">/dev/</code> (usualmente <code class="text-emerald-400">/dev/ttyUSB0</code> o <code class="text-emerald-400">/dev/ttyACM0</code>).
      </p>

      <div class="space-y-4 text-xs font-mono">
        <!-- Comando 1 -->
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div class="flex justify-between items-center mb-1 text-slate-400">
            <span class="font-sans font-semibold text-slate-300">1. Listar dispositivos USB / ACM:</span>
            <button @click="copyCommand(cmd1, 1)" class="text-cyan-400 hover:underline font-sans">
              {{ copiedIdx === 1 ? '¡Copiado!' : 'Copiar' }}
            </button>
          </div>
          <code class="text-emerald-300 block select-all">{{ cmd1 }}</code>
        </div>

        <!-- Comando 2 -->
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div class="flex justify-between items-center mb-1 text-slate-400">
            <span class="font-sans font-semibold text-slate-300">2. Ver mensajes del kernel al enchufar el USB:</span>
            <button @click="copyCommand(cmd2, 2)" class="text-cyan-400 hover:underline font-sans">
              {{ copiedIdx === 2 ? '¡Copiado!' : 'Copiar' }}
            </button>
          </div>
          <code class="text-emerald-300 block select-all">{{ cmd2 }}</code>
        </div>

        <!-- Comando 3 -->
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div class="flex justify-between items-center mb-1 text-slate-400">
            <span class="font-sans font-semibold text-slate-300">3. Si da error de permiso denegado (Permission Denied):</span>
            <button @click="copyCommand(cmd3, 3)" class="text-cyan-400 hover:underline font-sans">
              {{ copiedIdx === 3 ? '¡Copiado!' : 'Copiar' }}
            </button>
          </div>
          <code class="text-emerald-300 block select-all">{{ cmd3 }}</code>
          <p class="font-sans text-[11px] text-slate-400 mt-1">
            (Requiere reiniciar sesión o ejecutar <code class="text-slate-300">newgrp dialout</code> para aplicar).
          </p>
        </div>
      </div>

      <!-- Puertos detectados en tiempo real -->
      <div v-if="detectedPorts && detectedPorts.length > 0" class="mt-4 p-3 bg-slate-800/60 rounded border border-slate-700">
        <span class="text-xs font-semibold text-slate-300 block mb-2">Puertos detectados ahora mismo por el backend:</span>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="p in detectedPorts"
            :key="p.device"
            @click="$emit('select-port', p.device)"
            class="px-2 py-1 bg-cyan-950 hover:bg-cyan-800 text-cyan-300 border border-cyan-700 rounded text-xs font-mono"
          >
            {{ p.device }} ({{ p.description }})
          </button>
        </div>
      </div>

      <div class="mt-5 flex justify-end">
        <button @click="$emit('close')" class="btn btn-secondary text-sm">
          Entendido, cerrar
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  detectedPorts: {
    type: Array,
    default: () => []
  }
})

defineEmits(['close', 'select-port'])

const cmd1 = 'ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null'
const cmd2 = 'dmesg | grep -E "ttyUSB|ttyACM|ch341|cp210x|ftdi" | tail -n 10'
const cmd3 = 'sudo usermod -a -G dialout $USER'

const copiedIdx = ref(null)

const copyCommand = (txt, idx) => {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(txt)
  }
  copiedIdx.value = idx
  setTimeout(() => {
    copiedIdx.value = null
  }, 2000)
}
</script>
