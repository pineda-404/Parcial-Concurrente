const net = require('net');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const HOST = '127.0.0.1';
const PORT = 5002;

const client = new net.Socket();
client.connect(PORT, HOST, () => {
  console.log('Conectado al servidor de chat.');
  menu();
});

client.on('data', (data) => {
  console.log('[Respuesta]:', data.toString().trim());
  menu();
});

function menu() {
  console.log('\n--- CLIENTE CHAT ---');
  console.log('1. Consultar cuenta');
  console.log('2. Transferir dinero');
  console.log('3. Salir');
  rl.question('Seleccione: ', (op) => {
    if (op === '1') {
      rl.question('Cuenta: ', (acc) => {
        client.write(JSON.stringify({ type: "CONSULTAR_CUENTA", account: parseInt(acc) }) + "\n");
      });
    } else if (op === '2') {
      rl.question('Cuenta origen: ', (from) => {
        rl.question('Cuenta destino: ', (to) => {
          rl.question('Monto: ', (amt) => {
            client.write(JSON.stringify({ type: "TRANSFERIR_CUENTA", from: parseInt(from), to: parseInt(to), amount: parseFloat(amt) }) + "\n");
          });
        });
      });
    } else {
      rl.close();
      client.destroy();
    }
  });
}
