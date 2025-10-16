package nodo_trabajador;

import java.io.*;
import java.net.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.*;

public class NodoWorker {
    private int port;
    private final File dataFile;
    private final Map<Integer, Double> cuentas = new ConcurrentHashMap<>();
    private final Map<String, List<String>> preparedOps = new ConcurrentHashMap<>();
    private final Object localLock = new Object();

    public NodoWorker(int port, String dataFilePath) throws IOException {
        this.port = port;
        this.dataFile = new File(dataFilePath);
        loadData();
    }

    private void loadData() throws IOException {
        if (!dataFile.exists()) {
            dataFile.getParentFile().mkdirs();
            dataFile.createNewFile();
            return;
        }
        try (BufferedReader br = new BufferedReader(new FileReader(dataFile))) {
            String line;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;
                String[] p = line.split(",");
                if (p.length < 2) continue;
                try {
                    int id = Integer.parseInt(p[0].trim());
                    double bal = Double.parseDouble(p[1].trim());
                    cuentas.put(id, bal);
                } catch (NumberFormatException ex) {
                    System.err.println("[WARN] Línea inválida: " + line);
                }
            }
        }
        System.out.println("Nodo port " + port + " cargó " + cuentas.size() + " cuentas.");
    }

    private void persistToDisk() throws IOException {
        synchronized (localLock) {
            try (BufferedWriter bw = new BufferedWriter(new FileWriter(dataFile, false))) {
                for (Map.Entry<Integer, Double> e : cuentas.entrySet()) {
                    bw.write(e.getKey() + "," + String.format("%.2f", e.getValue()) + "\n");
                }
            }
        }
    }

    public void start() throws IOException {
        try (ServerSocket ss = new ServerSocket(port)) {
            System.out.println("NodoWorker escuchando en " + port);
            ExecutorService pool = Executors.newCachedThreadPool();
            while (true) {
                Socket s = ss.accept();
                pool.submit(() -> handleConn(s));
            }
        }
    }

    private void handleConn(Socket s) {
        try (BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream()));
             BufferedWriter out = new BufferedWriter(new OutputStreamWriter(s.getOutputStream()))) {

            String line;
            while ((line = in.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;
                System.out.println("[DEBUG NodoWorker] Mensaje recibido: " + line);

                Map<String,String> req = parseJson(line);
                String type = req.getOrDefault("type", "").toUpperCase();

                try {
                    switch (type) {
                        case "CONSULTAR_CUENTA":
                            handleConsulta(req, out);
                            break;
                        case "SUM_PARTITION":
                            handleSumPartition(out);
                            break;
                        case "PREPARE_TRANSFER":
                        case "PREPARE_CREATE":
                        case "PREPARE_DELETE":
                            handlePrepareMsg(req, out);
                            break;
                        case "COMMIT":
                            handleCommitMsg(req, out);
                            break;
                        case "ABORT":
                            handleAbortMsg(req, out);
                            break;
                        case "ESTADO_PAGO_PRESTAMO":
                            handlePrestamoConsulta(req, out);
                            break;
                        default:
                            out.write(jsonResponse("status","ERROR","error","TIPO_DESCONOCIDO") + "\n");
                            out.flush();
                            break;
                    }
                } catch (Exception inner) {
                    inner.printStackTrace();
                    out.write(jsonResponse("status","ERROR","error","EXCEPCION_EN_OPERACION") + "\n");
                    out.flush();
                }
            }
        } catch (Exception e) {
            System.err.println("Handler error nodo port " + port + ": " + e);
        }
    }

    private void handleConsulta(Map<String,String> req, BufferedWriter out) throws IOException {
        int acc = Integer.parseInt(req.get("account"));
        if (cuentas.containsKey(acc)) {
            double bal = cuentas.get(acc);
            String resp = jsonResponse("status","OK","account",String.valueOf(acc),"balance",String.format("%.2f",bal));
            out.write(resp + "\n");
            out.flush();
            System.out.println("[DEBUG NodoWorker] Respuesta enviada: " + resp);
        } else {
            out.write(jsonResponse("status","ERROR","error","NO_EXISTE_CUENTA") + "\n");
            out.flush();
        }
    }

    private void handleSumPartition(BufferedWriter out) throws IOException {
        double total = cuentas.values().stream().mapToDouble(Double::doubleValue).sum();
        String resp = jsonResponse("status","OK","sum",String.format("%.2f", total));
        out.write(resp + "\n");
        out.flush();
    }

    private void handlePrepareMsg(Map<String,String> req, BufferedWriter out) throws IOException {
        String tx = req.get("tx_id");
        boolean ok = handlePrepare(req, tx);
        out.write(ok ?
            jsonResponse("status","READY","tx_id",tx) + "\n" :
            jsonResponse("status","ERROR","tx_id",tx,"error","PREPARE_FAIL") + "\n");
        out.flush();
    }

    private void handleCommitMsg(Map<String,String> req, BufferedWriter out) throws IOException {
        String tx = req.get("tx_id");
        boolean ok = handleCommit(tx);
        out.write(ok ?
            jsonResponse("status","COMMITTED","tx_id",tx) + "\n" :
            jsonResponse("status","ERROR","tx_id",tx,"error","COMMIT_FAIL") + "\n");
        out.flush();
    }

    private void handleAbortMsg(Map<String,String> req, BufferedWriter out) throws IOException {
        String tx = req.get("tx_id");
        handleAbort(tx);
        out.write(jsonResponse("status","ABORTED","tx_id",tx) + "\n");
        out.flush();
    }

    private boolean handlePrepare(Map<String,String> req, String tx) {
        synchronized (localLock) {
            try {
                String type = req.get("type").toLowerCase();
                List<String> lst = new ArrayList<>();

                if (type.contains("transfer")) {
                    int from = Integer.parseInt(req.get("from"));
                    int to = Integer.parseInt(req.get("to"));
                    double amount = Double.parseDouble(req.get("amount"));

                    if (cuentas.containsKey(from)) {
                        if (cuentas.get(from) < amount) return false;
                        lst.add("debit," + from + "," + amount);
                    }
                    if (cuentas.containsKey(to)) {
                        lst.add("credit," + to + "," + amount);
                    }
                } else if (type.contains("create")) {
                    int acc = Integer.parseInt(req.get("account"));
                    double init = Double.parseDouble(req.get("initial"));
                    if (cuentas.containsKey(acc)) return false;
                    lst.add("create," + acc + "," + init);
                } else if (type.contains("delete")) {
                    int acc = Integer.parseInt(req.get("account"));
                    if (!cuentas.containsKey(acc)) return false;
                    lst.add("delete," + acc);
                }
                preparedOps.put(tx, lst);
                return true;
            } catch (Exception ex) {
                ex.printStackTrace();
                return false;
            }
        }
    }

    private boolean handleCommit(String tx) {
        synchronized (localLock) {
            List<String> ops = preparedOps.get(tx);
            if (ops == null) return false;
            String dbPath = System.getProperty("db.path", "db/banco_chat.db");
            try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
                for (String o : ops) {
                    String[] p = o.split(",");
                    String cmd = p[0];
                    if ("debit".equals(cmd)) {
                        int acc = Integer.parseInt(p[1]);
                        double amount = Double.parseDouble(p[2]);
                        cuentas.put(acc, cuentas.get(acc) - amount);
                        registrarTransaccion(db, acc, "Débito", amount);
                    } else if ("credit".equals(cmd)) {
                        int acc = Integer.parseInt(p[1]);
                        double amount = Double.parseDouble(p[2]);
                        cuentas.put(acc, cuentas.getOrDefault(acc, 0.0) + amount);
                        registrarTransaccion(db, acc, "Crédito", amount);
                    } else if ("create".equals(cmd)) {
                        int acc = Integer.parseInt(p[1]);
                        double init = Double.parseDouble(p[2]);
                        cuentas.put(acc, init);
                        registrarTransaccion(db, acc, "Creación de cuenta", init);
                    } else if ("delete".equals(cmd)) {
                        int acc = Integer.parseInt(p[1]);
                        cuentas.remove(acc);
                        registrarTransaccion(db, acc, "Eliminación de cuenta", 0);
                    }
                }
                persistToDisk();
                preparedOps.remove(tx);
                return true;
            } catch (Exception e) {
                e.printStackTrace();
                return false;
            }
        }
    }

    private void registrarTransaccion(Connection db, int idCuenta, String tipo, double monto) {
        try (PreparedStatement ps = db.prepareStatement("INSERT INTO Transacciones(id_cuenta,tipo,monto,fecha) VALUES(?,?,?,datetime('now'))")) {
            ps.setInt(1, idCuenta);
            ps.setString(2, tipo);
            ps.setDouble(3, monto);
            ps.executeUpdate();
        } catch (SQLException e) {
            System.err.println("[WARN] Error registrando transacción: " + e.getMessage());
        }
    }

    private void handlePrestamoConsulta(Map<String,String> req, BufferedWriter out) throws IOException {
        int acc = Integer.parseInt(req.get("account"));
        StringBuilder sb = new StringBuilder();
        String dbPath = System.getProperty("db.path", "db/banco_chat.db");
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + dbPath)) {
            PreparedStatement ps1 = c.prepareStatement("SELECT id_cliente FROM Cuentas WHERE id_cuenta=?");
            ps1.setInt(1, acc);
            ResultSet r1 = ps1.executeQuery();
            if (!r1.next()) {
                sb.append("{\"status\":\"ERROR\",\"error\":\"CUENTA_NO_EXISTE\"}");
            } else {
                int idcli = r1.getInt(1);
                PreparedStatement ps2 = c.prepareStatement("SELECT id_prestamo,monto,monto_pendiente,estado,fecha_solicitud FROM Prestamos WHERE id_cliente=?");
                ps2.setInt(1, idcli);
                ResultSet rs = ps2.executeQuery();
                sb.append("{\"status\":\"OK\",\"data\":[");
                boolean first = true;
                while (rs.next()) {
                    if (!first) sb.append(",");
                    sb.append(String.format("{\"id_prestamo\":%d,\"monto_total\":%.2f,\"monto_pendiente\":%.2f,\"estado\":\"%s\",\"fecha_solicitud\":\"%s\"}",
                        rs.getInt(1), rs.getDouble(2), rs.getDouble(3), rs.getString(4), rs.getString(5)));
                    first = false;
                }
                sb.append("]}");
            }
        } catch (Exception e) {
            sb.setLength(0);
            sb.append(String.format("{\"status\":\"ERROR\",\"error\":\"%s\"}", e.getMessage().replace('"', '\'')));
        }
        out.write(sb.toString() + "\n");
        out.flush();
    }

    private void handleAbort(String tx) {
        synchronized (localLock) {
            preparedOps.remove(tx);
        }
    }

    private String jsonResponse(String... kv) {
        StringBuilder sb = new StringBuilder("{");
        for (int i = 0; i < kv.length - 1; i += 2) {
            if (i > 0) sb.append(",");
            sb.append(String.format("\"%s\":", kv[i]));
            String v = kv[i + 1];
            try {
                Double.parseDouble(v);
                sb.append(v);
            } catch (NumberFormatException e) {
                sb.append(String.format("\"%s\"", v));
            }
        }
        sb.append("}");
        return sb.toString();
    }

    private Map<String, String> parseJson(String s) {
        Map<String, String> map = new HashMap<>();
        s = s.trim();
        if (!s.startsWith("{") || !s.endsWith("}")) return map;
        s = s.substring(1, s.length() - 1); // Remove braces

        String[] pairs = s.split(","); 
        for (String pair : pairs) {
            String[] kv = pair.split(":", 2);
            if (kv.length == 2) {
                String key = kv[0].trim().replace("\"", "");
                String value = kv[1].trim().replace("\"", "");
                map.put(key, value);
            }
        }
        return map;
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.out.println("Uso: java nodo_trabajador.NodoWorker <port> <datafile>");
            return;
        }
        int port = Integer.parseInt(args[0]);
        String dataFile = args[1];
        Class.forName("org.sqlite.JDBC");
        NodoWorker n = new NodoWorker(port, dataFile);
        n.start();
    }
}
