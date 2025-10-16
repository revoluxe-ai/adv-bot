# GRPC Predict CTR Service

<cite>
**Referenced Files in This Document**   
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [min_ctr_manager.py](file://app/modules/wb_adv_updater/min_ctr_manager/min_ctr_manager.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [predict_ctr_service_pb2.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2.py)
- [predict_ctr_service_pb2_grpc.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2_grpc.py)
- [redis_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/redis_manager.py)
- [predict_ctr.py](file://app/core/redis_manager_v2/mixins/predict_ctr.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The GRPC Predict CTR Service is a critical component in the advertising optimization system, providing click-through rate (CTR) predictions for Wildberries advertising campaigns. This service enables data-driven bidding decisions by predicting the likelihood of user clicks on specific product keywords. The system is built using gRPC for efficient communication between components, with a clear separation between the client interface, protocol definition, and integration points within the advertising workflow. The service supports both synchronous and asynchronous operations, with comprehensive error handling for network failures and service unavailability.

## Project Structure
The GRPC Predict CTR Service is organized in a modular structure within the application's modules directory. The service components are located in `app/modules/grpcs/predict_ctr_service/` and include the protocol definition, client implementation, configuration, and exception handling. The service is integrated with other components through dependency injection and follows a clean separation of concerns. The client implementation is designed for asynchronous operation, supporting modern Python async/await patterns for efficient resource utilization.

```mermaid
graph TB
subgraph "GRPC Predict CTR Service"
Proto[predict_ctr_service.proto]
Client[predict_ctr_client.py]
Config[config.py]
Excs[excs/excs.py]
Pb2[predict_ctr_service_pb2.py]
Pb2Grpc[predict_ctr_service_pb2_grpc.py]
end
subgraph "Integration Points"
PredictManager[predict_ctr_update_manager.py]
MinCtrManager[min_ctr_manager.py]
ML[ML.py]
end
subgraph "Configuration"
Settings[settings_master.py]
end
Proto --> Pb2
Proto --> Pb2Grpc
Pb2 --> Client
Pb2Grpc --> Client
Client --> PredictManager
Client --> MinCtrManager
Client --> ML
Config --> Client
Settings --> PredictManager
```

**Diagram sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [min_ctr_manager.py](file://app/modules/wb_adv_updater/min_ctr_manager/min_ctr_manager.py)
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [settings_master.py](file://app/settings/settings_master.py)

**Section sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)

## Core Components
The GRPC Predict CTR Service consists of several core components that work together to provide CTR prediction capabilities. The service is built around a well-defined protocol buffer contract that specifies the request and response formats. The client implementation provides a clean, asynchronous interface for interacting with the prediction service, handling connection lifecycle management and error conditions. Configuration is managed through both local settings and environment variables, allowing for flexible deployment across different environments. The service is integrated into the advertising workflow through dedicated managers that handle the business logic of when and how to use CTR predictions.

**Section sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [settings_master.py](file://app/settings/settings_master.py)

## Architecture Overview
The GRPC Predict CTR Service follows a client-server architecture with a clear separation between the service contract, client implementation, and integration points. The architecture is designed for high performance and reliability, with asynchronous operations throughout the stack. The service uses protocol buffers for efficient serialization and gRPC for reliable, high-performance communication. The client implementation manages connection pooling implicitly through the gRPC channel lifecycle, and supports context manager patterns for automatic resource cleanup.

```mermaid
sequenceDiagram
participant Client as PredictCTRClient
participant Stub as CtrServiceStub
participant Server as CtrService Server
participant Redis as Redis Storage
Client->>Client : Initialize with host : port
Client->>Client : async with PredictCTRClient
Client->>Client : await connect()
Client->>Stub : PredictCtr(request)
Stub->>Server : Send gRPC request
Server->>Server : Process prediction
Server->>Stub : Return response
Stub->>Client : Receive predictions
Client->>Redis : Save predictions via pipeline
Client->>Client : await close()
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service_pb2_grpc.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2_grpc.py)

## Detailed Component Analysis

### PredictCTRClient Analysis
The PredictCTRClient class provides a clean, asynchronous interface for interacting with the CTR prediction service. It handles connection lifecycle management, including automatic connection establishment and proper cleanup. The client supports both explicit connection management through connect()/close() methods and implicit management through async context manager usage. The predict() method accepts lists of nmids and phrases, packages them into the appropriate protocol buffer message, and returns the predictions as a dictionary.

#### For Object-Oriented Components:
```mermaid
classDiagram
class PredictCTRClient {
+string _target
+grpc.aio.Channel _channel
+CtrServiceStub _stub
+__init__(host : str, port : int)
+connect() void
+close() void
+predict(nmids : list[int], phrases : list[str]) dict[str, float]
+__aenter__() PredictCTRClient
+__aexit__() void
}
class CtrServiceStub {
+PredictCtr(request : PredictCtrRequest) PredictCtrResponse
}
PredictCTRClient --> CtrServiceStub : "uses"
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_service_pb2_grpc.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2_grpc.py)

#### For API/Service Components:
```mermaid
sequenceDiagram
participant App as Application
participant Client as PredictCTRClient
participant Stub as CtrServiceStub
participant Server as Prediction Server
App->>Client : client = PredictCTRClient(host, port)
App->>Client : async with client
Client->>Client : await connect()
Client->>Client : request = PredictCtrRequest(nmids, phrases)
Client->>Stub : await PredictCtr(request)
Stub->>Server : Send request
Server->>Stub : Return response
Stub->>Client : Receive response
Client->>App : Return predictions dict
App->>Client : Exit context
Client->>Client : await close()
```

**Diagram sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)

### Protocol Buffer Definition Analysis
The protocol buffer definition specifies the contract between the client and server, defining the structure of requests and responses. The PredictCtrRequest message contains two repeated fields: nmids (product identifiers) and phrases (search keywords). The PredictCtrResponse message contains a map of predictions, where each key is a phrase and the value is the predicted CTR. The CtrService service contract defines a single RPC method, PredictCtr, which takes a PredictCtrRequest and returns a PredictCtrResponse.

#### For Object-Oriented Components:
```mermaid
classDiagram
class PredictCtrRequest {
+repeated int64 nmids
+repeated string phrases
}
class PredictCtrResponse {
+map<string, float> predictions
}
class CtrService {
+PredictCtr(PredictCtrRequest) PredictCtrResponse
}
CtrService --> PredictCtrRequest : "input"
CtrService --> PredictCtrResponse : "output"
```

**Diagram sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)

**Section sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)

### Integration with Advertising Workflow
The PredictCTRClient is integrated into the advertising optimization workflow through several key components. The PredictCTRUpdateManager orchestrates the process of updating CTR predictions for advertising campaigns, while the MinCtrManager uses predictions to determine minimum CTR thresholds for bidding. The ML component uses predictions as part of its machine learning pipeline for campaign optimization.

#### For API/Service Components:
```mermaid
sequenceDiagram
participant Manager as PredictCTRUpdateManager
participant Client as PredictCTRClient
participant Redis as RedisManager
participant Adv as AdvSetting
Manager->>Manager : update_predict_ctr(adv, keywords)
Manager->>Manager : Extract nmids from adv
Manager->>Manager : Extract phrases from keywords
Manager->>Client : await client.predict(nmids, phrases)
Client->>Client : Create PredictCtrRequest
Client->>Client : Call PredictCtr RPC
Client->>Manager : Return predictions dict
Manager->>Redis : Save predictions via pipeline
Redis->>Redis : set_predict_ctr_with_pipeline()
Redis->>Manager : Confirm save
Manager->>Manager : Log results
```

**Diagram sources**
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [redis_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/redis_manager.py)

**Section sources**
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [redis_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/redis_manager.py)

## Dependency Analysis
The GRPC Predict CTR Service has a well-defined dependency structure that enables clean integration with the rest of the application. The service depends on gRPC and protocol buffers for communication, with generated code providing the interface between Python and the protocol definition. Configuration dependencies are managed through both local configuration files and environment variables, allowing for flexible deployment. The service is integrated into the application through dependency injection, with the PredictCTRUpdateManager container providing the necessary dependencies to the service components.

```mermaid
graph TD
subgraph "Core Dependencies"
GRPC[grpc]
Protobuf[google.protobuf]
end
subgraph "Service Components"
Proto[predict_ctr_service.proto]
Pb2[predict_ctr_service_pb2.py]
Pb2Grpc[predict_ctr_service_pb2_grpc.py]
Client[predict_ctr_client.py]
Config[config.py]
end
subgraph "Integration Components"
Manager[predict_ctr_update_manager.py]
RedisManager[redis_manager.py]
Settings[settings_master.py]
end
Proto --> Pb2
Proto --> Pb2Grpc
Pb2 --> Client
Pb2Grpc --> Client
Config --> Client
Settings --> Manager
Client --> Manager
Manager --> RedisManager
GRPC --> Pb2Grpc
Protobuf --> Pb2
```

**Diagram sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_service_pb2.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2.py)
- [predict_ctr_service_pb2_grpc.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2_grpc.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [settings_master.py](file://app/settings/settings_master.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [redis_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/redis_manager.py)

**Section sources**
- [predict_ctr_service.proto](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service.proto)
- [predict_ctr_service_pb2.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2.py)
- [predict_ctr_service_pb2_grpc.py](file://app/modules/grpcs/predict_ctr_service/grpc_service/predict_ctr_service_pb2_grpc.py)
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [config.py](file://app/modules/grpcs/predict_ctr_service/config.py)
- [settings_master.py](file://app/settings/settings_master.py)

## Performance Considerations
The GRPC Predict CTR Service is designed with performance in mind, leveraging asynchronous operations throughout the stack to maximize throughput and minimize latency. The service supports batch predictions, allowing multiple nmids and phrases to be processed in a single request, which reduces network overhead and improves efficiency. Connection pooling is handled implicitly by the gRPC channel, which maintains a pool of connections to the server for reuse across multiple requests. The client implementation uses pipelining when saving predictions to Redis, reducing the number of round trips to the storage layer. For high-volume scenarios, the service can be scaled horizontally by deploying multiple instances behind a load balancer.

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [redis_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/redis_manager.py)

## Troubleshooting Guide
When troubleshooting issues with the GRPC Predict CTR Service, several common scenarios should be considered. Network failures and timeout scenarios are handled through gRPC's built-in error handling, with specific error codes indicating the nature of the problem. Malformed responses are handled by validating the response structure and returning None when the response cannot be processed. Connection issues can be diagnosed by checking the service host and port configuration, as well as network connectivity between the client and server. Performance issues may indicate the need for connection pooling optimization or batch size adjustment. Logging is implemented throughout the service to provide visibility into the request/response flow and error conditions.

**Section sources**
- [predict_ctr_client.py](file://app/modules/grpcs/predict_ctr_service/predict_ctr_client/predict_ctr_client.py)
- [predict_ctr_update_manager.py](file://app/modules/shop_runner/service_manager/services/predict_ctr_update_manager/predict_ctr_update_manager.py)
- [excs.py](file://app/modules/grpcs/predict_ctr_service/excs/excs.py)

## Conclusion
The GRPC Predict CTR Service provides a robust, high-performance solution for CTR prediction in the advertising optimization system. The service's clean architecture, well-defined protocol, and comprehensive error handling make it a reliable component in the advertising workflow. The asynchronous design enables efficient resource utilization, while the integration with Redis and other components ensures seamless operation within the larger system. By following the documented patterns for connection management, error handling, and performance optimization, developers can effectively leverage the service to improve advertising campaign performance.