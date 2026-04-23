const express = require('express');
const app = express();
const path = require('path');
const http = require("http");
const { Server }  = require("socket.io");
const server = http.createServer(app);
const io = new Server(server);
const { spawn } = require("child_process");   // 🔥 IMPORTANT

/* ===============================
   🔥 PYTHON CHATBOT AUTO START
   =============================== */
const pythonPath = path.join(
  __dirname,
  "../foodin-chatbot/venv/Scripts/python.exe"
);

const pythonApp = path.join(
  __dirname,
  "../foodin-chatbot/app.py"
);

// 🔥 YAHI MISSING THA
const pythonProcess = spawn(pythonPath, [pythonApp], {
  stdio: "inherit"
});

pythonProcess.on("close", (code) => {
  console.log(`❌ Python chatbot stopped with code ${code}`);
});

/* ===============================
   EXPRESS WEBSITE
   =============================== */

app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, "public")));

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

app.get("/", (req, res) => {
  res.render("home");
});


server.listen(3030,"0.0.0.0", () => {
  console.log("Server running on port 3030");
});
