// Synthetic DOM probe. Run from the project root with Node; requires renderer dev dependencies.
import { harness, fixture } from '../../../broadcast_renderer/tests/harness.mjs';
const h = await harness();
try {
  const pending = [];
  h.w.fetch = path => String(path).includes('data.json')
    ? new Promise(resolve => pending.push(resolve))
    : Promise.resolve({ ok: true, text: async () => String(path).includes('Time.txt') ? '15:20' : '2' });
  const poll = h.intervals.find(i => i.ms === 250).callback;
  poll(); poll();
  const newer = fixture(); newer.team1.name = 'NUEVO'; newer.animation.status = 'hide';
  const older = fixture(); older.team1.name = 'ANTERIOR'; older.animation.status = 'show';
  pending[1]({ ok: true, json: async () => newer }); await h.flush();
  console.log('Respuesta nueva:', h.w.document.querySelector('.team1-name').value,
    h.w.document.getElementById('scoreboard-wrapper').className);
  pending[0]({ ok: true, json: async () => older }); await h.flush();
  console.log('Respuesta anterior retrasada:', h.w.document.querySelector('.team1-name').value,
    h.w.document.getElementById('scoreboard-wrapper').className);
} finally { h.close(); }
