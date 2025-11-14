import zmq from "zeromq";
import { randomBytes } from "crypto";
import { platform } from "os";

const reqAddress = "tcp://broker:5555";
const subAddress = "tcp://proxy:5558";
const username = `bot-${randomBytes(4).toString('hex')}`;

// Sockets
const reqSocket = new zmq.Request();
reqSocket.connect(reqAddress);

// O bot não precisa escutar, mas o socket sub é mantido para consistência futura
// const subSocket = new zmq.Subscriber();
// subSocket.connect(subAddress);

console.log(`Bot ${username} iniciado.`);

// --- Funções Auxiliares ZMQ ---

async function sendRequest(service, data) {
    const request = {
        service: service,
        data: data
    };
    
    // console.log(`[Bot REQ]: ${JSON.stringify(request)}`);
    await reqSocket.send(JSON.stringify(request));
    
    const [result] = await reqSocket.receive();
    const response = JSON.parse(result.toString());
    // console.log(`[Bot REP]: ${JSON.stringify(response)}`);
    return response.data;
}

// --- Lógica do Bot ---

async function run() {
    // 1. Fazer login
    try {
        await sendRequest("login", {
            user: username,
            timestamp: Math.floor(Date.now() / 1000)
        });
        console.log(`Bot ${username} fez login.`);
    } catch (e) {
        console.error("Erro no login do bot:", e);
        return;
    }

    // Loop principal de publicação
    while (true) {
        try {
            // 2. Obter lista de canais
            const channelsData = await sendRequest("channels", {
                timestamp: Math.floor(Date.now() / 1000)
            });
            
            // A API retorna a lista na chave "users" por engano na Etapa 1
            const channels = channelsData.users || []; 
            
            let targetChannel = "geral"; // Canal padrão
            if (channels.length > 0) {
                targetChannel = channels[Math.floor(Math.random() * channels.length)];
            } else {
                // Se não houver canais, cria um
                await sendRequest("channel", {
                    channel: targetChannel,
                    timestamp: Math.floor(Date.now() / 1000)
                });
                console.log(`Bot criou o canal padrão '${targetChannel}'`);
            }

            console.log(`Bot ${username} publicando 10 mensagens no canal '${targetChannel}'...`);
            
            // 3. Enviar 10 mensagens
            for (let i = 0; i < 10; i++) {
                const message = `Mensagem aleatória ${i} de ${username}`;
                await sendRequest("publish", {
                    user: username,
                    channel: targetChannel,
                    message: message,
                    timestamp: Math.floor(Date.now() / 1000)
                });
                // Pausa curta entre mensagens
                await new Promise(resolve => setTimeout(resolve, 100)); 
            }
            
            // 4. Esperar antes do próximo loop
            console.log("...Publicação concluída. Aguardando 5 segundos.");
            await new Promise(resolve => setTimeout(resolve, 5000));

        } catch (e) {
            console.error(`Bot ${username} encontrou um erro no loop:`, e);
            // Aguarda antes de tentar novamente
            await new Promise(resolve => setTimeout(resolve, 10000));
        }
    }
}

run();

// Lidar com o encerramento gracioso
process.on('SIGINT', () => {
    console.log('Encerrando sockets...');
    reqSocket.close();
    // subSocket.close();
    process.exit();
});