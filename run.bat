@echo off
REM Script para executar o sistema de impressão distribuída no Windows

echo ========================================
echo Sistema de Impressao Distribuida
echo Algoritmo Ricart-Agrawala com Lamport
echo ========================================
echo.

REM Gerar código Python a partir do .proto
echo [2/5] Gerando codigo gRPC a partir do .proto...
python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --proto_path=. printing.proto
if %errorlevel% neq 0 (
    echo ERRO: Falha ao gerar codigo gRPC
    pause
    exit /b 1
)
echo OK!
echo.

REM Verificar se as dependências estão instaladas
echo [1/5] Verificando dependencias...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Falha ao instalar dependencias
    pause
    exit /b 1
)
echo OK!
echo.

echo [3/5] Iniciando servidor de impressao...
start "Printer Server" cmd /k "python printer_server.py --port 50051"
timeout /t 2 >nul
echo OK!
echo.

echo [4/5] Iniciando Cliente 1 (porta 50052)...
start "Cliente 1" cmd /k "python printing_client.py --id 1 --port 50052 --clients localhost:50053,localhost:50054"
timeout /t 2 >nul
echo OK!
echo.

echo [5/5] Iniciando Cliente 2 (porta 50053)...
start "Cliente 2" cmd /k "python printing_client.py --id 2 --port 50053 --clients localhost:50052,localhost:50054"
timeout /t 2 >nul
echo OK!
echo.

echo Iniciando Cliente 3 (porta 50054)...
start "Cliente 3" cmd /k "python printing_client.py --id 3 --port 50054 --clients localhost:50052,localhost:50053"
echo OK!
echo.

echo ========================================
echo Sistema iniciado com sucesso!
echo ========================================
echo.
echo Observacoes:
echo - O servidor esta rodando na porta 50051
echo - Tres clientes estao rodando nas portas 50052, 50053 e 50054
echo - Cada cliente enviara requisicoes automaticamente em intervalos aleatorios
echo - Para parar, feche as janelas ou pressione Ctrl+C em cada terminal
echo.
pause