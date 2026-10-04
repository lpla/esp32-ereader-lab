// Bounded, source-free execution using the published WASM JavaScript API.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { initSync, WasmEmulator } from '../tools/esp-emu-0.45.0-wasm/www/pkg/esp_emu.js';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const image = process.argv[2] || 'firmware/x3-stock.bin';
const name = process.argv[3] || 'wasm-x3-stock';
const budget = Number(process.argv[4] || 10_000_000);
const result = path.join(root, 'results', name);
fs.mkdirSync(result, {recursive: true});
initSync({module: fs.readFileSync(path.join(root, 'tools/esp-emu-0.45.0-wasm/www/pkg/esp_emu_bg.wasm'))});
const emulator = new WasmEmulator('esp32c3');
emulator.load_default_rom();
emulator.set_boot_from_rom(true);
emulator.load_firmware(fs.readFileSync(path.join(root, image)));
const samples = [];
let uart = '';
let restarts = 0;
const start = performance.now();
for (let requested = 0; requested < budget && performance.now() - start < 15_000; requested += 50_000) {
  uart += emulator.run_batch(50_000);
  samples.push({requested: requested + 50_000, cycles: emulator.cycles().toString(), pc: '0x' + emulator.pc().toString(16)});
  if (emulator.needs_restart()) {
    restarts++;
    emulator.restart();
  }
}
const status = {image, requestedBudget: budget, wallMs: performance.now() - start,
  restarts, pc: '0x' + emulator.pc().toString(16), samples,
  api: Object.getOwnPropertyNames(WasmEmulator.prototype).filter(x => x !== 'constructor')};
fs.writeFileSync(path.join(result, 'uart.log'), uart);
fs.writeFileSync(path.join(result, 'status.json'), JSON.stringify(status, null, 2) + '\n');
emulator.free();
console.log(JSON.stringify({...status, samples: undefined}));
