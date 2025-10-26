# printing_client.py
import grpc
import threading
import time
import random
import argparse
from enum import Enum
from concurrent import futures

# Importar classes geradas
import printing_pb2
import printing_pb2_grpc

# Enum para representar o estado do cliente
class ClientState(Enum):
    LIBERADO = 1  # Não está na seção crítica e não quer entrar
    QUERENDO = 2  # Quer entrar na seção crítica
    EM_USO = 3    # Está na seção crítica

class Client:
    def __init__(self, client_id, port, server_addr, other_clients_addrs):
        # Identificação e endereços
        self.id = client_id
        self.port = port
        self.address = f"localhost:{port}"
        self.printer_server_address = server_addr
        self.other_clients_addresses = other_clients_addrs

        # Estado do algoritmo de Ricart-Agrawala
        self.state = ClientState.LIBERADO
        self.request_timestamp = -1
        self.replies_received = 0
        self.deferred_replies = []

        # Relógio Lógico de Lamport
        self.lamport_clock = 0

        # Lock para garantir a consistência dos dados em ambiente com threads
        self.lock = threading.Lock()

        # Stubs gRPC para comunicação com outros clientes
        self.client_stubs = {
            addr: printing_pb2_grpc.MutualExclusionServiceStub(grpc.insecure_channel(addr))
            for addr in self.other_clients_addresses
        }
        print(f"Cliente {self.id} conectou-se aos pares: {list(self.client_stubs.keys())}")

    # --- Lógica do Relógio de Lamport ---
    def tick(self):
        """ Incrementa o relógio local. Deve ser chamado antes de qualquer evento. """
        self.lamport_clock += 1

    def update_clock(self, received_timestamp):
        """ Atualiza o relógio local ao receber uma mensagem. """
        self.lamport_clock = max(self.lamport_clock, received_timestamp) + 1

    # --- Lógica de Ricart-Agrawala ---
    def request_access(self):
        """ Inicia o processo para solicitar acesso à seção crítica. """
        with self.lock:
            self.state = ClientState.QUERENDO
            self.tick()
            self.request_timestamp = self.lamport_clock
            self.replies_received = 0

            print(f"Cliente {self.id} [QUERENDO] | Relógio: {self.lamport_clock} | Pedido com timestamp: {self.request_timestamp}")

        if not self.other_clients_addresses:
            # Se não houver outros clientes, entra direto na seção crítica
            self.enter_critical_section()
            return

        # Envia pedido para todos os outros clientes
        request = printing_pb2.AccessRequest(
            client_id=self.id,
            lamport_timestamp=self.request_timestamp
        )
        for addr, stub in self.client_stubs.items():
            try:
                stub.RequestAccess(request)
                # A resposta é tratada implicitamente pelo bloqueio da chamada
                # ou pela lógica no servidor deste cliente.
                # Aqui, consideramos que a resposta foi recebida quando a chamada retorna.
                with self.lock:
                    self.replies_received += 1
            except grpc.RpcError as e:
                print(f"Cliente {self.id}: Erro ao contatar {addr}: {e.details()}")


    def enter_critical_section(self):
        """ Entra na seção crítica para usar a impressora. """
        with self.lock:
            self.state = ClientState.EM_USO
            self.tick()
            print(f"Cliente {self.id} [EM USO]   | Relógio: {self.lamport_clock} | Entrando na Seção Crítica...")

        try:
            with grpc.insecure_channel(self.printer_server_address) as channel:
                stub = printing_pb2_grpc.PrintingServiceStub(channel)
                message = f"Olá, impressora! Sou o cliente {self.id}."
                request = printing_pb2.PrintRequest(
                    client_id=self.id,
                    message_content=message,
                    lamport_timestamp=self.lamport_clock
                )
                response = stub.SendToPrinter(request)
                print(f"Cliente {self.id} recebeu do servidor: '{response.confirmation_message}'")
        except grpc.RpcError as e:
            print(f"Cliente {self.id}: Erro ao conectar com o servidor de impressão: {e.details()}")

        self.exit_critical_section()

    def exit_critical_section(self):
        """ Sai da seção crítica e responde às requisições pendentes. """
        with self.lock:
            self.state = ClientState.LIBERADO
            self.request_timestamp = -1
            print(f"Cliente {self.id} [LIBERADO] | Relógio: {self.lamport_clock} | Saindo da Seção Crítica.")

            # Responde a todas as requisições que foram adiadas
            for deferred_request, context in self.deferred_replies:
                context.set_code(grpc.StatusCode.OK)
                context.set_details('Access Granted')
                # A resposta em si é vazia, o importante é desbloquear o chamador
            self.deferred_replies.clear()

    # --- Lógica do Servidor gRPC do Cliente ---
    def serve(self):
        """ Inicia o servidor gRPC deste cliente para ouvir outros clientes. """
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        servicer = MutualExclusionServiceServicer(self)
        printing_pb2_grpc.add_MutualExclusionServiceServicer_to_server(servicer, server)
        server.add_insecure_port(self.address)
        server.start()
        print(f"Cliente {self.id} ouvindo na porta {self.port}.")
        server.wait_for_termination()

    def run(self):
        """ Inicia o servidor em uma thread e o loop principal do cliente. """
        server_thread = threading.Thread(target=self.serve, daemon=True)
        server_thread.start()

        # Aguarda um pouco para os servidores de todos os clientes estarem no ar
        time.sleep(5)

        while True:
            # Simula o desejo de imprimir em intervalos aleatórios
            time.sleep(random.uniform(5, 10))

            # Inicia o processo de solicitação de acesso
            self.request_access()

            # Espera por todas as respostas
            while True:
                with self.lock:
                    if self.replies_received >= len(self.other_clients_addresses):
                        break
                time.sleep(0.1)

            # Após receber todas as respostas, entra na seção crítica
            self.enter_critical_section()


class MutualExclusionServiceServicer(printing_pb2_grpc.MutualExclusionServiceServicer):
    """
    Implementa o serviço gRPC para que este cliente possa receber
    requisições de outros clientes.
    """
    def __init__(self, client_instance):
        self.client = client_instance

    def RequestAccess(self, request, context):
        """
        Lógica para tratar uma requisição de acesso de outro cliente.
        """
        with self.client.lock:
            self.client.update_clock(request.lamport_timestamp)
            print(f"Cliente {self.client.id} recebeu pedido de {request.client_id} (TS: {request.lamport_timestamp}) | Meu Relógio: {self.client.lamport_clock}")

            # Lógica de decisão de Ricart-Agrawala
            has_priority = (
                    self.client.request_timestamp < request.lamport_timestamp or
                    (self.client.request_timestamp == request.lamport_timestamp and self.client.id < request.client_id)
            )

            if self.client.state == ClientState.EM_USO or (self.client.state == ClientState.QUERENDO and has_priority):
                # Adia a resposta
                print(f"Cliente {self.client.id} adiou a resposta para o Cliente {request.client_id}")
                self.client.deferred_replies.append((request, context))
                # Mantém a conexão gRPC aberta esperando uma resposta futura
                return printing_pb2.AccessResponse()
            else:
                # Responde imediatamente
                print(f"Cliente {self.client.id} concedeu acesso imediato ao Cliente {request.client_id}")
                return printing_pb2.AccessResponse(access_granted=True)

def main():
    parser = argparse.ArgumentParser(description="Cliente para sistema de impressão distribuído.")
    parser.add_argument("--id", type=int, required=True, help="ID numérico do cliente.")
    parser.add_argument("--port", type=int, required=True, help="Porta para este cliente ouvir.")
    parser.add_argument("--server", type=str, default="localhost:50051", help="Endereço do servidor de impressão.")
    parser.add_argument("--clients", type=str, required=True, help="Lista de endereços dos outros clientes, separados por vírgula.")

    args = parser.parse_args()

    other_clients = [addr for addr in args.clients.split(',') if addr]

    client = Client(
        client_id=args.id,
        port=args.port,
        server_addr=args.server,
        other_clients_addrs=other_clients
    )
    client.run()

if __name__ == "__main__":
    main()
