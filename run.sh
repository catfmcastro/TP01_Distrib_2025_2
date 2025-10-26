#!/bin/bash

# run.sh
# Script para configurar e executar o sistema de impressão distribuído.

echo "--- Sistema de Impressão Distribuído ---"

# Função para encerrar todos os processos em background
cleanup() {
    echo ""
    echo "Encerrando todos os processos..."
    # A variável PIDS contém o ID de todos os processos iniciados
    for pid in "${PIDS[@]}"; do
        # Envia um sinal de término (SIGTERM) para cada processo
        kill "$pid" 2>/dev/null
    done
    echo "Sistema encerrado."
}

# Captura o sinal de interrupção (Ctrl+C) e de término para chamar a função de limpeza
trap cleanup EXIT SIGINT SIGTERM

# --- PASSO 1: Instalar dependências ---
echo "[1/5] Instalando dependências do requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Erro ao instalar as dependências. Verifique se 'pip' está instalado."
    exit 1
fi

# --- PASSO 2: Gerar código gRPC ---
echo "[2/5] Gerando código Python a partir de printing.proto..."
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. printing.proto
if [ $? -ne 0 ]; then
    echo "Erro ao gerar o código gRPC. Verifique se as ferramentas gRPC foram instaladas corretamente."
    exit 1
fi

# Array para armazenar os PIDs (Process IDs) dos processos em background
PIDS=()

# --- PASSO 3: Iniciar o Servidor de Impressão ---
echo "[3/5] Iniciando o servidor de impressão na porta 50051..."
python printer_server.py &
# Salva o PID do último processo iniciado em background
SERVER_PID=$!
PIDS+=("$SERVER_PID")
sleep 2 # Dá um tempo para o servidor iniciar completamente

# --- PASSO 4: Iniciar os Clientes ---
echo "[4/5] Iniciando 3 clientes inteligentes em background..."

# Cliente 1 (Ouve na 50052, conhece 50053 e 50054)
python printing_client.py --id 1 --port 50052 --clients localhost:50053,localhost:50054 &
PIDS+=("$!")
sleep 1

# Cliente 2 (Ouve na 50053, conhece 50052 e 50054)
python printing_client.py --id 2 --port 50053 --clients localhost:50052,localhost:50054 &
PIDS+=("$!")
sleep 1

# Cliente 3 (Ouve na 50054, conhece 50052 e 50053)
python printing_client.py --id 3 --port 50054 --clients localhost:50052,localhost:50053 &
PIDS+=("$!")
sleep 1

# --- PASSO 5: Manter em execução e aguardar encerramento ---
echo "[5/5] Sistema em execução."
echo "O servidor e 3 clientes estão rodando em background."
echo "Logs serão exibidos neste terminal."
echo ""
read -p "Pressione [ENTER] para encerrar todos os processos."

# A função cleanup será chamada automaticamente ao sair do script
exit 0
