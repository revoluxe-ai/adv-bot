# Payment Processing

<cite>
**Referenced Files in This Document**   
- [manager.py](file://app/payments/manager.py)
- [models.py](file://app/payments/db/models.py)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py)
- [handlers.py](file://app/modules/balance_manager/handlers.py)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [pricer.py](file://app/utils/pricer/pricer.py)
- [tariffs.py](file://app/utils/pricer/tariffs.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Payment System Architecture](#payment-system-architecture)
3. [Data Model for Payments](#data-model-for-payments)
4. [Payment Lifecycle](#payment-lifecycle)
5. [Integration with YooKassa](#integration-with-yookassa)
6. [Usage-Based Billing with Pricer](#usage-based-billing-with-pricer)
7. [Error Handling and Reconciliation](#error-handling-and-reconciliation)
8. [Security and Transaction Integrity](#security-and-transaction-integrity)
9. [Performance Considerations](#performance-considerations)
10. [Conclusion](#conclusion)

## Introduction
The adv-bot application implements a comprehensive payment processing system that enables users to manage advertising budgets through secure transactions. This document details the implementation of payment handling, including transaction recording, balance updates, integration with external providers like YooKassa, and usage-based billing calculations. The system is designed to handle high-volume operations while maintaining transaction integrity and security.

**Section sources**
- [manager.py](file://app/payments/manager.py#L1-L12)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

## Payment System Architecture
The payment system in adv-bot follows a modular architecture with clear separation of concerns between payment processing, balance management, and user interface components. The core functionality is distributed across several modules that work together to process payments, update balances, and maintain transaction records.

```mermaid
graph TD
A[User Interface] --> B[Payment Handler]
B --> C[Balance Service]
C --> D[Database]
E[YooKassa API] --> B
C --> F[Payment Model]
D --> G[WBCabinet]
D --> H[WBBalancePayment]
D --> I[WBBonusPayment]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333
style C fill:#bbf,stroke:#333
style D fill:#f96,stroke:#333
style E fill:#9f9,stroke:#333
style F fill:#f96,stroke:#333
style G fill:#f96,stroke:#333
style H fill:#f96,stroke:#333
style I fill:#f96,stroke:#333
```

**Diagram sources**
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

**Section sources**
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

## Data Model for Payments
The payment system utilizes a relational data model with several interconnected entities that track financial transactions and user balances. The core components include the Payment entity for system-wide transactions, WBBalancePayment for cabinet-specific balance changes, and WBCabinet for storing current balance states.

```mermaid
erDiagram
USER {
BIGINT id PK
BIGINT user_telegram_id UK
VARCHAR username
}
WBCABINET {
INTEGER id PK
VARCHAR shop_id UK
FLOAT balance
FLOAT bonus
BOOLEAN active
TIMESTAMP expiration_time
}
WBBALANCEPAYMENT {
INTEGER id PK
INTEGER wb_cabinet_id FK
FLOAT amount
TEXT description
TIMESTAMP transaction_date_time
}
WBBONUSSPAYMENT {
INTEGER id PK
INTEGER wb_cabinet_id FK
FLOAT amount
TEXT description
TIMESTAMP transaction_date_time
VARCHAR operation_type
INTEGER admin_user_id
}
PAYMENT {
INTEGER id PK
BIGINT user_id FK
BIGINT amount
VARCHAR target
TIMESTAMP timestamp
}
USER ||--o{ PAYMENT : "has"
WBCABINET ||--o{ WBBALANCEPAYMENT : "has"
WBCABINET ||--o{ WBBONUSPAYMENT : "has"
WBCABINET ||--o{ WBUSERCABINET : "has"
```

**Diagram sources**
- [models.py](file://app/utils/db/models.py#L1-L52)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L1-L199)
- [models.py](file://app/payments/db/models.py#L1-L12)

**Section sources**
- [models.py](file://app/utils/db/models.py#L1-L52)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L1-L199)
- [models.py](file://app/payments/db/models.py#L1-L12)

## Payment Lifecycle
The payment lifecycle in adv-bot follows a structured process from initiation to confirmation and balance update. This sequence ensures transaction integrity and provides a seamless user experience through the Telegram interface.

```mermaid
sequenceDiagram
participant User as "Telegram User"
participant Handler as "Balance Handler"
participant Service as "Balance Service"
participant YooKassa as "YooKassa API"
participant DB as "Database"
User->>Handler : Click "Add Balance"
Handler->>Handler : Show Terms & Conditions
Handler->>User : Request Amount Input
User->>Handler : Enter Amount
Handler->>YooKassa : Create Invoice
YooKassa-->>User : Payment Interface
User->>YooKassa : Complete Payment
YooKassa->>Handler : Pre-Checkout Query
Handler->>Handler : Validate Payment
Handler-->>YooKassa : Confirm Payment
YooKassa->>Handler : Successful Payment Webhook
Handler->>Service : Process Payment with Bonus
Service->>DB : Create WBBalancePayment
Service->>DB : Create Payment Record
Service-->>Handler : Return Payment Details
Handler->>User : Confirm Balance Update
```

**Diagram sources**
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

**Section sources**
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

## Integration with YooKassa
The adv-bot application integrates with YooKassa, a popular Russian payment provider, to handle secure financial transactions. The integration is configured using account credentials and implements Telegram's payment API for a seamless user experience.

```mermaid
flowchart TD
A[Configure YooKassa] --> B[Create Payment Payload]
B --> C[Send Invoice via Telegram]
C --> D[User Completes Payment]
D --> E[Handle Pre-Checkout Query]
E --> F[Process Successful Payment]
F --> G[Update Balance in Database]
G --> H[Send Confirmation to User]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333
style C fill:#bbf,stroke:#333
style D fill:#9f9,stroke:#333
style E fill:#bbf,stroke:#333
style F fill:#bbf,stroke:#333
style G fill:#f96,stroke:#333
style H fill:#bbf,stroke:#333
```

**Diagram sources**
- [manager.py](file://app/payments/manager.py#L1-L12)
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)

**Section sources**
- [manager.py](file://app/payments/manager.py#L1-L12)
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)

## Usage-Based Billing with Pricer
The pricer module implements a usage-based billing system that calculates charges based on the number of active advertising settings per shop. The pricing model uses tiered tariffs that provide volume discounts for larger numbers of advertisements.

```mermaid
classDiagram
class Pricer {
+tariffs : dict
+text : str
+get_advs_count(shop_id) : int
+get_month_tariff_for_count_advs(shop_id) : int
+get_price_for_day_for_shop(shop_id) : float
+get_price_for_count_advs_in_cabinet_for_month(count_advs) : int
+get_payment_for_adv(sum_payment, count_advs) : float
+get_automactic_tariff(shop_id) : int
}
class tariffs {
+2 : 1699
+5 : 1299
+10 : 899
+20 : 799
+50 : 649
+150 : 549
+500 : 399
}
Pricer --> tariffs : "uses"
```

**Diagram sources**
- [pricer.py](file://app/utils/pricer/pricer.py#L1-L105)
- [tariffs.py](file://app/utils/pricer/tariffs.py#L1-L9)

**Section sources**
- [pricer.py](file://app/utils/pricer/pricer.py#L1-L105)
- [tariffs.py](file://app/utils/pricer/tariffs.py#L1-L9)

## Error Handling and Reconciliation
The payment system implements robust error handling to address common issues such as failed payments, duplicate transactions, and reconciliation challenges. The architecture includes validation at multiple levels to ensure data consistency and transaction integrity.

```mermaid
flowchart TD
A[Payment Initiated] --> B{Valid Amount?}
B --> |No| C[Reject with Error]
B --> |Yes| D{User Exists?}
D --> |No| E[Log Error, Notify Support]
D --> |Yes| F[Create Payment Record]
F --> G{Payment Confirmed?}
G --> |No| H[Mark as Failed]
G --> |Yes| I[Update Balance]
I --> J{Bonus Applicable?}
J --> |Yes| K[Create Bonus Payment]
J --> |No| L[Complete Transaction]
K --> L
L --> M[Send Confirmation]
style C fill:#f66,stroke:#333
style E fill:#f66,stroke:#333
style H fill:#f66,stroke:#333
style M fill:#6f6,stroke:#333
```

**Diagram sources**
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)

**Section sources**
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)
- [handlers.py](file://app/modules/balance_manager/handlers.py#L1-L226)

## Security and Transaction Integrity
The payment system prioritizes security and transaction integrity through multiple mechanisms including idempotency, proper error handling, and database constraints. These measures ensure that financial operations are reliable and protected against common vulnerabilities.

```mermaid
flowchart TD
A[Secure Configuration] --> B[Input Validation]
B --> C[Idempotent Operations]
C --> D[Database Transactions]
D --> E[Error Logging]
E --> F[Audit Trail]
F --> G[Reconciliation Process]
style A fill:#f9f,stroke:#333
style B fill:#bbf,stroke:#333
style C fill:#bbf,stroke:#333
style D fill:#f96,stroke:#333
style E fill:#f96,stroke:#333
style F fill:#f96,stroke:#333
style G fill:#f96,stroke:#333
```

**Diagram sources**
- [manager.py](file://app/payments/manager.py#L1-L12)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

**Section sources**
- [manager.py](file://app/payments/manager.py#L1-L12)
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)

## Performance Considerations
The payment system is designed to handle high-volume operations efficiently through optimized database queries, appropriate indexing, and asynchronous processing. These performance considerations ensure responsive user experiences even during peak usage periods.

```mermaid
flowchart TD
A[Asynchronous Processing] --> B[Database Indexing]
B --> C[Read-Only Sessions]
C --> D[Cached Balance Calculations]
D --> E[Batch Operations]
E --> F[Connection Pooling]
style A fill:#f9f,stroke:#333
style B fill:#f96,stroke:#333
style C fill:#f96,stroke:#333
style D fill:#f96,stroke:#333
style E fill:#f96,stroke:#333
style F fill:#f96,stroke:#333
```

**Diagram sources**
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)
- [pricer.py](file://app/utils/pricer/pricer.py#L1-L105)

**Section sources**
- [balance_service.py](file://app/modules/balance_manager/balance_service.py#L1-L235)
- [pricer.py](file://app/utils/pricer/pricer.py#L1-L105)

## Conclusion
The payment processing system in adv-bot provides a comprehensive solution for managing advertising budgets through secure, reliable transactions. By integrating with YooKassa and implementing a usage-based billing model, the system offers flexibility and scalability for users with varying needs. The architecture emphasizes security, transaction integrity, and performance, ensuring a robust foundation for financial operations within the application.