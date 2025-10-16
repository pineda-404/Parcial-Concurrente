const net = require('net');

const CENTRAL_HOST = '127.0.0.1';
const CENTRAL_PORT = 6000;
const CHAT_PORT = 5002;

const server = net.createServer((client) => {
  console.log(`[ChatServer] Cliente conectado`);
  client.on('data', (data) => {
    const msg = data.toString().trim();
    console.log(`[ChatServer] Recibido: ${msg}`);
    const socketCentral = new net.Socket();
    socketCentral.connect(CENTRAL_PORT, CENTRAL_HOST, () => {
      socketCentral.write(msg + "\n");
    });
    socketCentral.on('data', (resp) => {
      client.write(resp.toString() + "\n");
      socketCentral.destroy();
    });
  });
  client.on('close', () => console.log(`[ChatServer] Cliente desconectado`));
});

server.listen(CHAT_PORT, '127.0.0.1', () => {
  console.log(`[ChatServer] Escuchando en ${CHAT_PORT}`);
});
