CREATE TABLE ClienteChat (
    id_cliente_chat INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    fecha_conexion DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE MensajesChat (
    id_mensaje INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente_chat INTEGER,
    mensaje TEXT,
    respuesta TEXT,
    fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
    tipo_mensaje TEXT,
    FOREIGN KEY(id_cliente_chat) REFERENCES ClienteChat(id_cliente_chat)
);

CREATE TABLE AvisosServidor (
    id_aviso INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER,
    tipo_aviso TEXT,
    contenido TEXT,
    fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Cuentas (
    id_cuenta INTEGER PRIMARY KEY,
    id_cliente INTEGER,
    saldo REAL,
    fecha_apertura DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Transacciones (
    id_transaccion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cuenta INTEGER,
    tipo TEXT,
    monto REAL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_cuenta) REFERENCES Cuentas(id_cuenta)
);

CREATE TABLE Prestamos (
    id_prestamo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER,
    monto REAL,
    monto_pendiente REAL,
    estado TEXT,
    fecha_solicitud DATETIME DEFAULT CURRENT_TIMESTAMP
);
