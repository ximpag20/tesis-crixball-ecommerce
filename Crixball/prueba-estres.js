import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 50 },   // sube a 50 usuarios en 1 minuto
    { duration: '1m', target: 100 },  // sube a 100 usuarios
    { duration: '1m', target: 150 },  // sube a 150 usuarios
    { duration: '1m', target: 200 },  // sube a 200 usuarios
    { duration: '1m', target: 250 },  // sube a 250 usuarios
    { duration: '1m', target: 300 },  // sube a 300 usuarios
    { duration: '1m', target: 350 },  // sube a 350 usuarios
    { duration: '1m', target: 400 },  // sube a 400 usuarios
    { duration: '1m', target: 450 },  // sube a 450 usuarios
    { duration: '1m', target: 500 },  // hasta 500
  ],
};

export default function () {
  const res = http.get('https://sistemacrixball.onrender.com/');
  check(res, {
    'status es 200': (r) => r.status === 200,
  });
}
