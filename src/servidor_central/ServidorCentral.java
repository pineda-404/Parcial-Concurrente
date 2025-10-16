// ServidorCentral.java
package servidor_central;

import java.io.*;
import java.net.*;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.*;
import java.util.concurrent.*;

/**
 * ServidorCentral (versión corregida y funcional)
 * Coordina nodos con protocolo 2PC.
 * Uso: java ServidorCentral <port> <config.json>
 */
public class ServidorCentral {

    private int port;
    private int partitions;
    private final Map<Integer, List<NodeInfo>> partitionsMap = new HashMap<>();
    private final ExecutorService pool = Executors.newCachedThreadPool();
    private final Random rnd = new Random();

    static class NodeInfo {
        int id;
        String host;
        int port;

        NodeInfo(int id, String host, int port) {
            this.id = id;
            this.host = host;
            this.port = port;
        }

        @Override
        public String toString() {
            return String.format("Node{id=%d,host=%s,port=%d}", id, host, port);
        }
    }

    public ServidorCentral(int port, String configFile) throws Exception {
        this.port = port;
        loadConfig(configFile);
    }

    /**
     * Lee el archivo JSON de configuración y extrae nodos.
     * No usa librerías externas (solo parsing básico).
     */
    private void loadConfig(String configPath) throws IOException {
        String content = new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(configPath)));
        content = content.replaceAll("\\s+", "");

        // Leer cantidad de particiones
        int idxPart = content.indexOf("\"partitions\":");
        if (idxPart < 0)
            throw new IOException("Campo partitions no encontrado en config");
        int startPart = idxPart + "\"partitions\":".length();
        int endPart = content.indexOf(",", startPart);
        if (endPart < 0)
            endPart = content.indexOf("}", startPart);
        partitions = Integer.parseInt(content.substring(startPart, endPart));

        // Buscar el bloque de partitions_map
        int idxMap = content.indexOf("\"partitions_map\":{");
        if (idxMap < 0)
            throw new IOException("Campo partitions_map no encontrado en config");
        int startMap = idxMap + "\"partitions_map\":{".length();
        int endMap = content.lastIndexOf("}");
        String mapBlock = content.substring(startMap, endMap);

        for (int p = 0; p < partitions; p++) {
            String key = "\"" + p + "\":[";
            int pos = mapBlock.indexOf(key);
            if (pos < 0)
                continue;
            int arrStart = pos + key.length();
            int arrEnd = mapBlock.indexOf("]", arrStart);
            String arrayBlock = mapBlock.substring(arrStart, arrEnd);
            String[] nodes = arrayBlock.split("\\},\\{");

            List<NodeInfo> list = new ArrayList<>();
            for (String node : nodes) {
                node = node.replace("{", "").replace("}", "");
                String[] pairs = node.split(",");
                int id = -1, port = -1;
                String host = "127.0.0.1";
                for (String pair : pairs) {
                    String[] kv = pair.split(":");
                    if (kv.length != 2)
                        continue;
                    String k = kv[0].replace("\"", "");
                    String v = kv[1].replace("\"", "");
                    switch (k) {
                        case "id":
                            id = Integer.parseInt(v);
                            break;
                        case "port":
                            port = Integer.parseInt(v);
                            break;
                        case "host":
                            host = v;
                            break;
                    }
                }
                if (id != -1 && port != -1)
                    list.add(new NodeInfo(id, host, port));
            }
            partitionsMap.put(p, list);
        }

        System.out.println("Configuración cargada. Particiones: " + partitions);
        partitionsMap.forEach((k, v) -> System.out.println("Partición " + k + " -> " + v));
    }

    /** Inicio del servidor central */
    public void start() throws IOException {
        try (ServerSocket ss = new ServerSocket(port)) {
            System.out.println("[ServidorCentral] Escuchando en puerto " + port);
            while (true) {
                Socket c = ss.accept();
                pool.submit(() -> handleConnection(c));
            }
        }
    }

    /** Maneja la conexión de un cliente o servidor */
    private void handleConnection(Socket s) {
        try (BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream()));
                BufferedWriter out = new BufferedWriter(new OutputStreamWriter(s.getOutputStream()))) {

            String line;
            while ((line = in.readLine()) != null) {
                if (line.trim().isEmpty())
                    continue;
                Map<String, String> req = parseJson(line);
                String type = req.get("type");
                if (type != null)
                    type = type.toUpperCase();

                if ("CONSULTAR_CUENTA".equals(type)) {
                    int acc = Integer.parseInt(req.get("account"));
                    int p = acc % partitions; // Correct partitioning logic
                    String resp = forwardToPartition(p, line); // Fault-tolerant forward
                    out.write(resp + "\n");
                    out.flush();

                } else if ("TRANSFERIR_CUENTA".equals(type)) {
                    int from = Integer.parseInt(req.get("from"));
                    int to = Integer.parseInt(req.get("to"));
                    double amount = Double.parseDouble(req.get("amount"));
                    String tx = "tx_" + System.currentTimeMillis();
                    boolean ok = twoPhaseCommitTransfer(tx, from, to, amount);
                    out.write(ok ? "{\"status\":\"OK\"}\n" : "{\"status\":\"ERROR\"}\n");
                    out.flush();

                } else if ("CREAR_CUENTA".equals(type)) {
                    int acc = Integer.parseInt(req.get("account"));
                    double init = Double.parseDouble(req.get("initial"));
                    String tx = "tx_" + System.currentTimeMillis();
                    boolean ok = twoPhaseCommitCreate(tx, acc, init);
                    out.write(ok ? "{\"status\":\"OK\"}\n" : "{\"status\":\"ERROR\"}\n");
                    out.flush();

                } else if ("ELIMINAR_CUENTA".equals(type)) {
                    int acc = Integer.parseInt(req.get("account"));
                    String tx = "tx_" + System.currentTimeMillis();
                    boolean ok = twoPhaseCommitDelete(tx, acc);
                    out.write(ok ? "{\"status\":\"OK\"}\n" : "{\"status\":\"ERROR\"}\n");
                    out.flush();

                }
                // === NUEVO: Consultar transacciones desde SQLite ===
                else if ("CONSULTAR_TRANSACCIONES".equals(type)) {
                    int acc = Integer.parseInt(req.get("account"));
                    StringBuilder sb = new StringBuilder("{\"status\":\"OK\",\"data\":[");
                    try (Connection c = DriverManager.getConnection("jdbc:sqlite:python/db/banco_chat.db")) {
                        PreparedStatement ps = c.prepareStatement(
                                "SELECT id_transaccion,tipo,monto,fecha FROM Transacciones WHERE id_cuenta=? ORDER BY fecha DESC LIMIT 20");
                        ps.setInt(1, acc);
                        ResultSet rs = ps.executeQuery();
                        boolean first = true;
                        while (rs.next()) {
                            if (!first)
                                sb.append(",");
                            sb.append("{\"id\":").append(rs.getInt(1))
                                    .append(",\"tipo\":\"").append(rs.getString(2))
                                    .append("\",\"monto\":").append(rs.getDouble(3))
                                    .append(",\"fecha\":\"").append(rs.getString(4)).append("\"}");
                            first = false;
                        }
                        sb.append("]}");
                    } catch (Exception e) {
                        sb.setLength(0);
                        sb.append("{\"status\":\"ERROR\",\"error\":\"").append(e.getMessage()).append("\"}");
                    }
                    out.write(sb.toString() + "\n");
                    out.flush();
                }

                // === NUEVO: Consultar préstamos desde SQLite ===
                else if ("ESTADO_PAGO_PRESTAMO".equals(type)) {
                    int acc = Integer.parseInt(req.get("account"));
                    StringBuilder sb = new StringBuilder();
                    try (Connection c = DriverManager.getConnection("jdbc:sqlite:python/db/banco_chat.db")) {
                        PreparedStatement ps1 = c.prepareStatement("SELECT id_cliente FROM Cuentas WHERE id_cuenta=?");
                        ps1.setInt(1, acc);
                        ResultSet r1 = ps1.executeQuery();
                        if (!r1.next()) {
                            sb.append("{\"status\":\"ERROR\",\"error\":\"CUENTA_NO_EXISTE\"}");
                        } else {
                            int idcli = r1.getInt(1);
                            PreparedStatement ps2 = c.prepareStatement(
                                    "SELECT id_prestamo,monto,monto_pendiente,estado,fecha_solicitud FROM Prestamos WHERE id_cliente=?");
                            ps2.setInt(1, idcli);
                            ResultSet rs = ps2.executeQuery();
                            sb.append("{\"status\":\"OK\",\"data\":[");
                            boolean first = true;
                            while (rs.next()) {
                                if (!first)
                                    sb.append(",");
                                sb.append("{\"id_prestamo\":").append(rs.getInt(1))
                                        .append(",\"monto_total\":").append(rs.getDouble(2))
                                        .append(",\"monto_pendiente\":").append(rs.getDouble(3))
                                        .append(",\"estado\":\"").append(rs.getString(4))
                                        .append("\",\"fecha_solicitud\":\"").append(rs.getString(5)).append("\"}");
                                first = false;
                            }
                            sb.append("]}");
                        }
                    } catch (Exception e) {
                        sb.setLength(0);
                        sb.append("{\"status\":\"ERROR\",\"error\":\"").append(e.getMessage()).append("\"}");
                    }
                    out.write(sb.toString() + "\n");
                    out.flush();
                }

                // === NUEVO: Arqueo de Cuentas ===
                else if ("ARQUEO".equals(type)) {
                    double totalBalance = 0.0;
                    boolean error = false;
                    for (int p = 0; p < partitions; p++) {
                        String respStr = forwardToPartition(p, "{\"type\":\"SUM_PARTITION\"}");
                        try {
                            Map<String, String> resp = parseJson(respStr);
                            if ("OK".equals(resp.get("status"))) {
                                totalBalance += Double.parseDouble(resp.get("sum"));
                            } else {
                                error = true;
                                break;
                            }
                        } catch (Exception e) {
                            error = true;
                            break;
                        }
                    }
                    if (error) {
                        out.write("{\"status\":\"ERROR\",\"error\":\"Fallo el arqueo en alguna particion\"}\n");
                    } else {
                        out.write(String.format("{\"status\":\"OK\",\"total_balance\":%.2f}\n", totalBalance));
                    }
                    out.flush();
                }

                else {
                    out.write("{\"status\":\"ERROR\",\"error\":\"Tipo desconocido\"}\n");
                    out.flush();
                }
            }

        } catch (Exception e) {
            System.err.println("[Error Central] " + e.getMessage());
        }
    }

    /** Envía una petición JSON simple a un nodo */
    private String forward(NodeInfo node, String json) {
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress(node.host, node.port), 1000); // 1 segundo timeout de conexión
            s.setSoTimeout(5000); // 5 segundos timeout de lectura
            try (BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream()));
                 BufferedWriter out = new BufferedWriter(new OutputStreamWriter(s.getOutputStream()))) {
                out.write(json + "\n");
                out.flush();
                String resp = in.readLine();
                return resp != null ? resp : "{\"status\":\"ERROR\",\"error\":\"sin respuesta\"}";
            }
        } catch (Exception e) {
            System.err.println("[Error Central] Nodo " + node + " inalcanzable: " + e.getMessage());
            return "{\"status\":\"ERROR\",\"error\":\"nodo inalcanzable\"}";
        }
    }

    /** Envía una petición a una partición, con reintentos en réplicas */
    private String forwardToPartition(int partition, String json) {
        List<NodeInfo> nodes = partitionsMap.get(partition);
        if (nodes == null || nodes.isEmpty()) {
            return "{\"status\":\"ERROR\",\"error\":\"particion no configurada\"}";
        }
        for (NodeInfo node : nodes) {
            String resp = forward(node, json);
            if (!resp.contains("nodo inalcanzable")) {
                return resp;
            }
        }
        return "{\"status\":\"ERROR\",\"error\":\"particion inalcanzable\"}";
    }

    /** Implementación de 2PC para transferencias con tolerancia a fallos */
    private boolean twoPhaseCommitTransfer(String tx, int from, int to, double amount) {
        int pFrom = from % partitions;
        int pTo = to % partitions;
        Set<NodeInfo> participants = new HashSet<>();
        if (partitionsMap.containsKey(pFrom)) participants.addAll(partitionsMap.get(pFrom));
        if (partitionsMap.containsKey(pTo)) participants.addAll(partitionsMap.get(pTo));

        // Phase 1: Prepare
        List<NodeInfo> preparedNodes = new CopyOnWriteArrayList<>();
        participants.parallelStream().forEach(n -> {
            String prep = "{\"type\":\"PREPARE_TRANSFER\",\"tx_id\":\"" + tx + "\",\"from\":" + from +
                    ",\"to\":" + to + ",\"amount\":" + amount + "}";
            String resp = forward(n, prep);
            if (resp != null && resp.contains("READY")) {
                preparedNodes.add(n);
            }
        });

        if (preparedNodes.size() < participants.size()) {
            preparedNodes.parallelStream().forEach(n -> forward(n, "{\"type\":\"ABORT\",\"tx_id\":\"" + tx + "\"}"));
            return false;
        }

        preparedNodes.parallelStream().forEach(n -> forward(n, "{\"type\":\"COMMIT\",\"tx_id\":\"" + tx + "\"}"));
        return true;
    }

    /** CREATE con 2PC y tolerancia a fallos */
    private boolean twoPhaseCommitCreate(String tx, int acc, double init) {
        int p = acc % partitions;
        List<NodeInfo> nodes = partitionsMap.get(p);
        if (nodes == null || nodes.isEmpty()) return false;

        // Phase 1: Prepare
        List<NodeInfo> preparedNodes = new CopyOnWriteArrayList<>();
        nodes.parallelStream().forEach(n -> {
            String msg = "{\"type\":\"PREPARE_CREATE\",\"tx_id\":\"" + tx + "\",\"account\":" + acc +
                    ",\"initial\":" + init + "}";
            String resp = forward(n, msg);
            if (resp != null && resp.contains("READY")) {
                preparedNodes.add(n);
            }
        });

        if (preparedNodes.size() < nodes.size()) {
            preparedNodes.parallelStream().forEach(n -> forward(n, "{\"type\":\"ABORT\",\"tx_id\":\"" + tx + "\"}"));
            return false;
        }

        preparedNodes.parallelStream().forEach(n -> forward(n, "{\"type\":\"COMMIT\",\"tx_id\":\"" + tx + "\"}"));
        return true;
    }

    /** DELETE con 2PC y tolerancia a fallos */
    private boolean twoPhaseCommitDelete(String tx, int acc) {
        int p = acc % partitions;
        List<NodeInfo> nodes = partitionsMap.get(p);
        if (nodes == null || nodes.isEmpty()) return false;

        List<NodeInfo> preparedNodes = new CopyOnWriteArrayList<>();
        nodes.parallelStream().forEach(n -> {
            String msg = "{\"type\":\"PREPARE_DELETE\",\"tx_id\":\"" + tx + "\",\"account\":" + acc + "}";
            String resp = forward(n, msg);
            if (resp != null && resp.contains("READY")) {
                preparedNodes.add(n);
            }
        });

        if (preparedNodes.size() < nodes.size()) {
            preparedNodes.parallelStream().forEach(n -> forward(n, "{\"type\":\"ABORT\",\"tx_id\":\"" + tx + "\"}"));
            return false;
        }

        preparedNodes.parallelStream().forEach(n -> forward(n, "{\"type\":\"COMMIT\",\"tx_id\":\"" + tx + "\"}"));
        return true;
    }

    /** Parser JSON extremadamente simple (sin dependencias) */
    private Map<String, String> parseJson(String s) {
        Map<String, String> map = new HashMap<>();
        s = s.trim();
        if (!s.startsWith("{") || !s.endsWith("}"))
            return map;
        s = s.substring(1, s.length() - 1); // quitar { }

        String[] pairs = s.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)");
        for (String kv : pairs) {
            String[] pair = kv.split(":(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", 2);
            if (pair.length == 2) {
                String key = pair[0].trim().replaceAll("^\"|\"$", "");
                String value = pair[1].trim().replaceAll("^\"|\"$", "");
                map.put(key, value);
            }
        }
        return map;
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.out.println("Uso: java ServidorCentral <port> <config.json>");
            return;
        }
        int port = Integer.parseInt(args[0]);
        String cfg = args[1];
        Class.forName("org.sqlite.JDBC"); // Cargar driver SQLite
        ServidorCentral sc = new ServidorCentral(port, cfg);
        sc.start();
    }
}
