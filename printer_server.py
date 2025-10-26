# printer_server.py
import grpc
from concurrent import futures
import time
import random

# Importar classes geradas
import printing_pb2
import printing_pb2_grpc

class PrintingServiceServicer(printing_pb2_grpc.PrintingServiceServicer):
    """
    Implementa o serviço gRPC para o servidor de impressão.
    """
    def SendToPrinter(self, request, context):
        """
        Recebe uma requisição de impressão, simula o trabalho e retorna uma confirmação.
        """
        client_id = request.client_id
        timestamp = request.lamport_timestamp
        message = request.message_content

        print(f"[Servidor de Impressão] Recebido pedido do Cliente {client_id} (Relógio: {timestamp})")
        print(f"[Servidor de Impressão] Imprimindo: '{message}'")

        # Simula o tempo de impressão
        print_duration = random.uniform(2, 3)
        time.sleep(print_duration)

        confirmation_msg = f"Trabalho do Cliente {client_id} concluído em {print_duration:.2f} segundos."
        print(f"[Servidor de Impressão] {confirmation_msg}")

        return printing_pb2.PrintResponse(
            success=True,
            confirmation_message=confirmation_msg
        )

def serve():
    """
    Inicia o servidor gRPC e o mantém em execução.
    """
    port = '50051'
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    printing_pb2_grpc.add_PrintingServiceServicer_to_server(PrintingServiceServicer(), server)
    server.add_insecure_port('[::]:' + port)
    server.start()
    print(f"Servidor de Impressão 'Burro' iniciado na porta {port}.")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Servidor de Impressão encerrado.")
        server.stop(0)

if __name__ == '__main__':
    serve()
