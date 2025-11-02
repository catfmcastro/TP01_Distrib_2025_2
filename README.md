# Sistema de Impressão Distribuído (Manual de Uso)

## Descrição

Sistema de impressão distribuído construído com gRPC, composto por 1 servidor e 3 clientes em Python.

## Pré-requisitos

- Python 3
- pip (gerenciador de pacotes Python)

## Instalação

### 1. Instalar dependências

Execute o comando a seguir para instalar as bibliotecas necessárias (gRPC e Protocol Buffers):

```bash
pip install -r requirements.txt
```

### 2. Compilar arquivo .proto

Antes de executar o sistema, compile o arquivo `printing.proto` para gerar os stubs gRPC em Python:

```bash
python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --proto_path=. printing.proto
```

## Execução

O sistema é composto por 4 processos que devem ser executados em terminais separados.

### Terminal 1: Servidor de Impressão

Inicia o servidor na porta 50051:

```bash
python printer_server.py
```

### Terminal 2: Cliente 1

Inicia o Cliente 1, ouvindo na porta 50052:

```bash
python printing_client.py --id 1 --port 50052 --clients localhost:50053,localhost:50054
```

### Terminal 3: Cliente 2

Inicia o Cliente 2, ouvindo na porta 50053:

```bash
python printing_client.py --id 2 --port 50053 --clients localhost:50052,localhost:50054
```

### Terminal 4: Cliente 3

Inicia o Cliente 3, ouvindo na porta 50054:

```bash
python printing_client.py --id 3 --port 50054 --clients localhost:50052,localhost:50053
```

## Notas

- O servidor define internamente a porta 50051
- Cada cliente se conecta aos outros dois clientes nas portas especificadas
- Certifique-se de executar cada processo em um terminal separado
