import express from "express";
import fs from "fs";
import path from "path";
import bodyParser from "body-parser";
import base64 from "base-64";
import dotenv from "dotenv";

dotenv.config();
const app = express();
const port = 3001;

app.use(bodyParser.json());

const ordensDeProducao = {
  REC00001: [
    {
      id_ordem: "ORDEMPROD-0001",
      desc_ordem_producao: "Ordem de Produção 001",
      codigo_produto: "01-01-00001",
      detalhes: "ABC-123",
      qtde: "5",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    },
    {
      id_ordem: "ORDEMPROD-0002",
      desc_ordem_producao: "Ordem de Produção 002",
      codigo_produto: "01-01-00002",
      detalhes: "ABC-123",
      qtde: "3",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    },
    {
      id_ordem: "ORDEMPROD-0003",
      desc_ordem_producao: "Ordem de Produção 003",
      codigo_produto: "01-01-00003",
      detalhes: "ABC-123",
      qtde: "5000",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    }
  ],
  REC00002: [
    {
      id_ordem: "ORDEMPROD-0004",
      desc_ordem_producao: "Ordem de Produção 001",
      codigo_produto: "01-01-00001",
      detalhes: "ABC-123",
      qtde: "5",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    },
    {
      id_ordem: "ORDEMPROD-0005",
      desc_ordem_producao: "Ordem de Produção 002",
      codigo_produto: "01-01-00002",
      detalhes: "ABC-123",
      qtde: "3",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    },
    {
      id_ordem: "ORDEMPROD-0006",
      desc_ordem_producao: "Ordem de Produção 003",
      codigo_produto: "01-01-00003",
      detalhes: "ABC-123",
      qtde: "5000",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    }
  ],
  REC00003: [
    {
      id_ordem: "ORDEMPROD-0007",
      desc_ordem_producao: "Ordem de Produção 001",
      codigo_produto: "01-01-00001",
      detalhes: "ABC-123",
      qtde: "5",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    },
    {
      id_ordem: "ORDEMPROD-0008",
      desc_ordem_producao: "Ordem de Produção 002",
      codigo_produto: "01-01-00002",
      detalhes: "ABC-123",
      qtde: "3",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    },
    {
      id_ordem: "ORDEMPROD-0009",
      desc_ordem_producao: "Ordem de Produção 003",
      codigo_produto: "01-01-00003",
      detalhes: "ABC-123",
      qtde: "5000",
      dt_conclusao_estimada: new Date().toISOString().split("T")[0]
    }
  ],



};

const ordemDefault = [
  {
    id_ordem: "SEM OP ESPECIFICADA",
    desc_ordem_producao: "",
    codigo_produto: "",
    detalhes: "",
    qtde: "",
    dt_conclusao_estimada: ""
  }
];

const logFiles = {
  get: path.resolve("./log_gets.log"),
  post: path.resolve("./log_requests.log")
};

function adicionarRegistro(data, tipo = "GET") {
  const logFile = tipo === "POST" ? logFiles.post : logFiles.get;
  fs.appendFileSync(logFile, JSON.stringify(data, null, 2) + ",\n", "utf-8");
}

function validateBasicAuth(token) {
  try {
    const decoded = base64.decode(token);
    const [username, password] = decoded.split(":");
    const validUsers = {
      david: "123",
      adolfo: "123"
    };
    return validUsers[username] === password ? username : null;
  } catch {
    return null;
  }
}

// GET /
app.get("/", (req, res) => {
  const { idmachine, group, search } = req.query;
  if (!idmachine && !group) return res.status(400).json({ error: "Especifique o recurso ou grupo" });
  let data = ordensDeProducao[idmachine] || ordemDefault;
  if (search) {
    data = data.filter(
      (ordem) =>
        ordem.id_ordem.includes(search) ||
        ordem.codigo_produto.includes(search)
    );
  }
	const meta = {};
	meta["idmachine"]=idmachine
	meta["group"]=group
	meta["search"]=search
  adicionarRegistro(data, "GET");
  return res.json([data, meta]);
});

// GET /logs_get
app.get("/logs_get", (req, res) => {
  try {
    if (!fs.existsSync(logFiles.get))
      return res.status(404).json({ error: "Log file not found" });

    const content = fs.readFileSync(logFiles.get, "utf-8").trim();
    if (!content) return res.json({ content: [], message: "Log vazio" });

    const jsonArray = JSON.parse("[" + content.replace(/,\s*$/, "") + "]");
    res.json({ total_entries: jsonArray.length, content: jsonArray });
  } catch (err) {
    res.status(500).json({ error: `Error reading log: ${err.message}` });
  }
});

// GET /logs_post
app.get("/logs_post", (req, res) => {
  try {
    if (!fs.existsSync(logFiles.post))
      return res.status(404).json({ error: "Log file not found" });

    const content = fs.readFileSync(logFiles.post, "utf-8").trim();
    if (!content) return res.json({ content: [], message: "Log vazio" });

    const jsonArray = JSON.parse("[" + content.replace(/,\s*$/, "") + "]");
    res.json({
      total_entries: jsonArray.length,
      content: jsonArray.reverse()
    });
  } catch (err) {
    res.status(500).json({ error: `Error reading log: ${err.message}` });
  }
});

// POST /
app.post("/", (req, res) => {
  try {
    const data = req.body;
    if (!data) return res.status(400).json({ error: "No JSON data provided" });

    adicionarRegistro(data, "POST");

    const auth = req.headers.authorization || "";
    let username = "unknown";

    if (auth.startsWith("Basic ")) {
      const token = auth.replace("Basic ", "");
      username = validateBasicAuth(token) || "invalid_user";
    } else if (auth.startsWith("Bearer ")) {
      username = "token_user";
    }

    return res.json({
      message: `Dados recebidos com sucesso: ${username} validado`,
      data
    });
  } catch (err) {
    res.status(400).json({ error: `Invalid JSON data: ${err.message}` });
  }
});

// POST /debug
let counter = 0;
app.post("/debug", (req, res) => {
  try {
    const data = req.body;
    if (!data) return res.status(400).json({ error: "No JSON data provided" });

    if (parseInt(data.NAME.slice(-1)) % 2 !== 0 && counter > 0) {
      counter--;
      console.log(`${data.NAME} falha numero ${counter}`);
      return res.status(400).json({ error: "Odd number in name" });
    }

    console.log(`Recebido: ${data.NAME}`);
    adicionarRegistro(data, "POST");
    counter = 5;

    const auth = req.headers.authorization || "";
    let username = "unknown";
    if (auth.startsWith("Basic ")) {
      const token = auth.replace("Basic ", "");
      username = validateBasicAuth(token) || "invalid_user";
    } else if (auth.startsWith("Bearer ")) {
      username = "token_user";
    }

    return res.json({
      message: `Dados recebidos com sucesso: ${username} validado`,
      data
    });
  } catch (err) {
    res.status(400).json({ error: `Invalid JSON data: ${err.message}` });
  }
});

app.listen(port, () => {
  console.log(`🚀 API rodando em http://204.216.182.116:${port}`);
});

