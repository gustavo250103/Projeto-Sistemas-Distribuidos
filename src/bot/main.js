import zmq from "zeromq";
import { randomBytes } from "crypto";
import { encode, decode } from "@msgpack/msgpack";

const reqAddress = "tcp://broker:5555";
const username = `bot-${randomBytes(4).toString("hex")}`;

const reqSocket = new zmq.Request();
reqSocket.connect(reqAddress);

let logicalClock = 0;

const incrementClock = () => {
  logicalClock += 1;
  return logicalClock;
};

const updateClock = (received) => {
  if (typeof received !== "number") return logicalClock;
  logicalClock = Math.max(logicalClock, received);
  return logicalClock;
};

console.log(`Bot ${username} iniciado.`);

async function sendRequest(service, data) {
  const request = {
    service,
    data: {
      ...data,
      clock: incrementClock(),
    },
  };
  await reqSocket.send(encode(request));
  const [result] = await reqSocket.receive();
  const response = decode(result);
  updateClock(response?.data?.clock);
  return response.data;
}

async function run() {
  try {
    await sendRequest("login", {
      user: username,
      timestamp: Math.floor(Date.now() / 1000),
    });
    console.log(`Bot ${username} fez login.`);
  } catch (e) {
    console.error("Erro no login do bot:", e);
    return;
  }

  while (true) {
    try {
      const channelsData = await sendRequest("channels", {
        timestamp: Math.floor(Date.now() / 1000),
      });

      const channels = channelsData.users || [];
      let targetChannel = "geral";
      if (channels.length > 0) {
        targetChannel = channels[Math.floor(Math.random() * channels.length)];
      } else {
        await sendRequest("channel", {
          channel: targetChannel,
          timestamp: Math.floor(Date.now() / 1000),
        });
        console.log(`Bot criou o canal padrão '${targetChannel}'`);
      }

      console.log(
        `Bot ${username} publicando 10 mensagens no canal '${targetChannel}'...`
      );

      for (let i = 0; i < 10; i++) {
        const message = `Mensagem aleatória ${i} de ${username}`;
        await sendRequest("publish", {
          user: username,
          channel: targetChannel,
          message: message,
          timestamp: Math.floor(Date.now() / 1000),
        });
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      console.log("...Publicação concluída. Aguardando 5 segundos.");
      await new Promise((resolve) => setTimeout(resolve, 5000));
    } catch (e) {
      console.error(`Bot ${username} encontrou um erro no loop:`, e);
      await new Promise((resolve) => setTimeout(resolve, 10000));
    }
  }
}

run();

process.on("SIGINT", () => {
  console.log("Encerrando sockets...");
  reqSocket.close();
  process.exit();
});
