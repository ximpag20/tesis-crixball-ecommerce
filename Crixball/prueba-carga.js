import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 10 },   // Comienza con 10 usuarios
    { duration: '1m', target: 30 },   // Sube a 30
    { duration: '2m', target: 60 },   // Luego sube a 60
    { duration: '2m', target: 80 },   // Finalmente hasta 80 usuarios
    { duration: '1m', target: 30 },   // Baja gradualmente
    { duration: '1m', target: 0 },    // Finaliza la prueba
  ],
};

export default function () {
  let res = http.get('https://sistemacrixball.onrender.com/contactos/');

  check(res, {
    'status es 200': (r) => r.status === 200,
    'carga en menos de 1s': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
