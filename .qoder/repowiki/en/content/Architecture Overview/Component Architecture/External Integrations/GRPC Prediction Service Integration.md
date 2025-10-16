# GRPC Prediction Service Integration

<cite>
**Referenced Files in This Document**   
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [excs.py](file://app/modules/grpcs/predict_ctr_service/excs/excs.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [GRPC Service Architecture](#grpc-service-architecture)
3. [PredictCTRClient Implementation](#predictctrclient-implementation)
4. [Request/Response Structure](#requestresponse-structure)
5. [Connection Management](#connection-management)
6. [Error Handling and Retry Strategies](#error-handling-and-retry-strategies)
7. [Integration with PredictCTRUpdateManager](#integration-with-predictctrupdatemanager)
8. [Configuration Parameters](#configuration-parameters)
9. [Security Considerations](#security-considerations)
10. [Performance and Connection Pooling](#performance-and-connection-pooling)

## Introduction
The GRPC Prediction Service Integration provides a high-performance interface for predicting click-through rates (CTR) for advertising campaigns. This documentation details the implementation of the PredictCTRClient, its integration with the advertising optimization system, and the underlying architecture that enables efficient communication with the prediction service. The system is designed to support asynchronous operations, robust error handling, and seamless integration with the broader advertising management platform.

## GRPC Service Architecture

```mermaid
graph TD
subgraph "Client Application"
A[PredictCTRClient] --> B[PredictCTRUpdateManager]
B --> C[Redis Storage]
B --> D[Database]
end
subgraph "GRPC Service"
E[CtrService]
F[Prediction Model]
G[Data Processing]
end
A --> |gRPC Request| E
E --> |Response| A
```

**Diagram sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)

**Section sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

## PredictCTRClient Implementation

The PredictCTRClient class provides an asynchronous interface for communicating with the CTR prediction service. It encapsulates the gRPC channel management, request serialization, and response handling in a clean, reusable component.

```mermaid
classDiagram
class PredictCTRClient {
+str _target
+grpc.aio.Channel _channel
+CtrServiceStub _stub
+__init__(host : str, port : int)
+connect() void
+close() void
+predict(nmids : list[int], phrases : list[str]) dict[str, float] | None
+__aenter__() PredictCTRClient
+__aexit__(exc_type, exc_val, exc_tb) void
}
class CtrServiceStub {
+PredictCtr(request : PredictCtrRequest) PredictCtrResponse
}
PredictCTRClient --> CtrServiceStub : "uses"
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service_pb2_grpc.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2_grpc.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

## Request/Response Structure

The service uses Protocol Buffers for efficient serialization of requests and responses. The message structure is defined in the predict_ctr_service.proto file.

```mermaid
erDiagram
PREDICT_CTR_REQUEST {
repeated int64 nmids PK
repeated string phrases PK
}
PREDICT_CTR_RESPONSE {
map predictions PK
}
PREDICT_CTR_REQUEST ||--o{ PREDICT_CTR_RESPONSE : "generates"
```

**Diagram sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)

**Section sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)

## Connection Management

The PredictCTRClient implements asynchronous connection management with lazy initialization and proper resource cleanup. The client establishes a connection only when needed and maintains it for subsequent requests.

```mermaid
sequenceDiagram
participant Client as PredictCTRClient
participant Channel as grpc.aio.Channel
participant Stub as CtrServiceStub
Client->>Client : predict(nmids, phrases)
alt Channel not established
Client->>Client : connect()
Client->>Channel : grpc.aio.insecure_channel(target)
Channel-->>Client : Channel
Client->>Client : _stub = CtrServiceStub(channel)
end
Client->>Stub : PredictCtr(request)
Stub-->>Client : response
Client->>Client : return dict(predictions)
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

## Error Handling and Retry Strategies

The integration includes comprehensive error handling for various failure scenarios, including network issues, service unavailability, and invalid requests.

```mermaid
flowchart TD
Start([predict method]) --> ValidateInput["Validate Input Parameters"]
ValidateInput --> CheckConnection{"Connection Established?"}
CheckConnection --> |No| EstablishConnection["Create gRPC Channel"]
EstablishConnection --> |Failed| HandleConnectionError["Handle Connection Error"]
CheckConnection --> |Yes| SendRequest["Send gRPC Request"]
SendRequest --> |Success| ProcessResponse["Process Response"]
SendRequest --> |gRPC Error| HandleGRPCError["Handle gRPC Error"]
HandleGRPCError --> |UNAVAILABLE| Retry["Schedule Retry"]
HandleGRPCError --> |INVALID_ARGUMENT| ReturnError["Return Error"]
HandleGRPCError --> |Other| LogError["Log Error"]
ProcessResponse --> |Valid| ReturnPredictions["Return Predictions"]
ProcessResponse --> |Empty| LogWarning["Log Warning"]
ReturnPredictions --> End([Method Exit])
ReturnError --> End
LogError --> End
LogWarning --> End
Retry --> End
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [excs.py](file://app/modules/grpcs/predict_ctr_service/excs/excs.py)

## Integration with PredictCTRUpdateManager

The PredictCTRUpdateManager orchestrates the prediction workflow, integrating the gRPC client with Redis storage and database operations for advertising optimization.

```mermaid
sequenceDiagram
participant Manager as PredictCTRUpdateManager
participant Client as PredictCTRClient
participant Redis as RedisStorage
participant DB as Database
Manager->>Manager : update_predict_ctr(adv, keywords_coro)
Manager->>Manager : await keywords_coro
Manager->>Manager : extract nmids and phrases
Manager->>Client : get gRPC client
Client->>Client : connect if needed
Client-->>Manager : client
Manager->>Client : predict(nmids, phrases)
Client->>Service : Send gRPC request
Service-->>Client : Return predictions
Client-->>Manager : predictions
alt Predictions valid
Manager->>Redis : save_predictions_to_redis
Redis-->>Manager : confirmation
else Predictions invalid
Manager->>Manager : log warning
end
Manager->>Manager : handle any exceptions
Manager-->>Caller : completion
```

**Diagram sources**
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

**Section sources**
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)

## Configuration Parameters

The integration uses configurable parameters for host, port, and other connection settings, allowing for flexible deployment across different environments.

```mermaid
classDiagram
class Configuration {
+str PREDICT_CTR_HOST
+int PREDICT_CTR_PORT
+str HOST
+int PORT
}
class PredictCTRClient {
+str _target
+int port
}
class Settings {
+str PREDICT_CTR_HOST
+int PREDICT_CTR_PORT
}
PredictCTRClient --> Configuration : "uses"
PredictCTRUpdateManager --> Settings : "uses"
```

**Diagram sources**
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

**Section sources**
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [settings_master.py](file://app/settings/settings_master.py)

## Security Considerations

The current implementation uses insecure gRPC channels, which has important security implications for production deployment.

```mermaid
flowchart LR
A[Client] --> |Insecure Channel| B[GRPC Server]
B --> C[No Encryption]
B --> D[No Authentication]
C --> E[Data in Transit Vulnerable]
D --> F[No Identity Verification]
E --> G[Recommendations]
F --> G[Recommendations]
G --> H[Implement TLS/SSL]
G --> I[Add Authentication]
G --> J[Use Secure Endpoints]
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [run_grpc_services.py](file://run_grpc_services.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

## Performance and Connection Pooling

The architecture supports efficient connection management and performance optimization for high-throughput scenarios.

```mermaid
graph TD
subgraph "Connection Management"
A[Connection Pool] --> B[Active Channel 1]
A --> C[Active Channel 2]
A --> D[Active Channel N]
E[Connection Factory] --> A
end
subgraph "Request Processing"
F[Request 1] --> |Uses| B
G[Request 2] --> |Uses| C
H[Request N] --> |Uses| D
end
I[Connection Reuse] --> J[Reduced Latency]
K[Async Operations] --> L[High Throughput]
J --> M[Optimized Performance]
L --> M
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)