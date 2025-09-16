# Subscription Management

<cite>
**Referenced Files in This Document**   
- [tariffs.py](file://app/utils/pricer/tariffs.py)
- [pricer.py](file://app/utils/pricer/pricer.py)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [settings_master.py](file://app/settings/settings_master.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Tiered Pricing Model](#tiered-pricing-model)
3. [Dynamic Pricing Implementation](#dynamic-pricing-implementation)
4. [Subscription Lifecycle and Payment Processing](#subscription-lifecycle-and-payment-processing)
5. [Feature Availability and Subscription Status](#feature-availability-and-subscription-status)
6. [Data Flow and Balance Management](#data-flow-and-balance-management)
7. [Common Issues and Recovery Procedures](#common-issues-and-recovery-procedures)
8. [Performance Considerations](#performance-considerations)

## Introduction
The Subscription Management system in the adv-bot application implements a dynamic pricing model based on the number of advertising campaigns per shop. This document details the implementation of tiered pricing, daily/monthly tariff calculations, payment processing logic, and the relationship between subscription status and feature availability. The system automatically calculates costs based on campaign count, processes payments from user balances, and manages subscription states to ensure service continuity.

## Tiered Pricing Model
The subscription system implements a tiered pricing model where the cost per advertising campaign decreases as the number of campaigns increases. This incentivizes users to manage more campaigns through the platform while maintaining revenue stability.

```mermaid
flowchart TD
A["Number of Campaigns"] --> B{Tier Evaluation}
B --> |≤ 2| C["1,699 ₽ per campaign"]
B --> |≤ 5| D["1,299 ₽ per campaign"]
B --> |≤ 10| E["899 ₽ per campaign"]
B --> |≤ 20| F["799 ₽ per campaign"]
B --> |≤ 50| G["649 ₽ per campaign"]
B --> |≤ 150| H["549 ₽ per campaign"]
B --> |≤ 500| I["399 ₽ per campaign"]
B --> |> 500| J["399 ₽ per campaign"]
```

**Diagram sources**
- [tariffs.py](file://app/utils/pricer/tariffs.py#L1-L8)

**Section sources**
- [tariffs.py](file://app/utils/pricer/tariffs.py#L1-L8)
- [pricer.py](file://app/utils/pricer/pricer.py#L25-L45)

## Dynamic Pricing Implementation
The pricing system dynamically calculates subscription costs based on the number of active advertising campaigns associated with a shop. The implementation uses a tiered structure where higher campaign volumes receive discounted rates per campaign.

The pricing algorithm works as follows:
1. Count the number of active advertising campaigns for a shop
2. Determine the appropriate pricing tier based on campaign count
3. Calculate total monthly cost by multiplying campaign count by tier-specific rate
4. Convert monthly cost to daily cost for automated deductions

```mermaid
sequenceDiagram
participant User as "Shop Owner"
participant Pricer as "Pricer Class"
participant DB as "Database"
User->>Pricer : Request subscription cost
Pricer->>DB : Query active campaign count
DB-->>Pricer : Return campaign count
Pricer->>Pricer : Determine pricing tier
Pricer->>Pricer : Calculate monthly cost
Pricer->>Pricer : Convert to daily cost
Pricer-->>User : Return daily/monthly costs
```

**Diagram sources**
- [pricer.py](file://app/utils/pricer/pricer.py#L25-L85)

**Section sources**
- [pricer.py](file://app/utils/pricer/pricer.py#L25-L85)

## Subscription Lifecycle and Payment Processing
The subscription lifecycle begins with user registration and continues through automated payment processing, status checks, and service provisioning. The system processes payments daily by checking campaign counts, calculating costs, and deducting amounts from user balances.

```mermaid
flowchart TD
Start([User Registration]) --> CreateShop["Create Shop Profile"]
CreateShop --> AddCampaigns["Add Advertising Campaigns"]
AddCampaigns --> CalculateCost["Calculate Subscription Cost"]
CalculateCost --> CheckBalance["Check Available Balance"]
CheckBalance --> |Sufficient| DeductPayment["Deduct Daily Payment"]
CheckBalance --> |Insufficient| SuspendService["Suspend Services"]
DeductPayment --> UpdateStatus["Update Subscription Status"]
SuspendService --> NotifyUser["Notify User"]
NotifyUser --> TopUpBalance["Balance Top-up"]
TopUpBalance --> ResumeService["Resume Services"]
UpdateStatus --> ActiveService["Active Service"]
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L45-L120)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L45-L120)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L150-L200)

## Feature Availability and Subscription Status
Subscription status directly controls feature availability within the application. When payments are current, all features remain active. Payment failures trigger automatic service restrictions to prevent unauthorized usage.

The relationship between subscription status and feature availability is implemented as follows:

```mermaid
classDiagram
class SubscriptionStatus {
+active : bool
+bot_active : bool
+auto_update_white_list : bool
+auto_update_target_place : bool
}
class FeatureAvailability {
+bidder_active : bool
+parsing_active : bool
+clusters_mode : bool
+target_ctr_mode : bool
}
class PaymentStatus {
+calculated_balance : float
+calculated_bonus : float
+has_sufficient_funds : bool
}
SubscriptionStatus --> FeatureAvailability : "controls"
PaymentStatus --> SubscriptionStatus : "determines"
FeatureAvailability --> SubscriptionStatus : "reflects"
```

When a payment fails due to insufficient balance, the system automatically deactivates key features by setting:
- `bot_active = False`
- `auto_update_white_list = False` 
- `auto_update_target_place = False`

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L95-L115)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L300-L350)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L95-L115)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L300-L350)

## Data Flow and Balance Management
The system implements a comprehensive balance management system that tracks both main balance and bonus funds. Payment processing follows a priority order, first using bonus funds and then main balance when bonuses are depleted.

```mermaid
flowchart LR
A["Payment Processing"] --> B["Check Bonus Balance"]
B --> |Sufficient| C["Deduct from Bonus"]
B --> |Insufficient| D["Check Main Balance"]
D --> |Sufficient| E["Deduct from Main Balance"]
D --> |Insufficient| F["Deactivate Services"]
C --> G["Record Bonus Payment"]
E --> H["Record Balance Payment"]
G --> I["Update Subscription Status"]
H --> I
F --> I
```

The balance calculation uses hybrid properties that combine initial balance values with transaction histories:

- `calculated_balance = balance + sum(payment.amount for payment in balance_payments)`
- `calculated_bonus = bonus + sum(payment.amount for payment in bonus_payments)`

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L60-L95)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L100-L130)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L60-L95)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L100-L130)

## Common Issues and Recovery Procedures
The system addresses several common subscription management issues with automated procedures:

### Insufficient Balance
When a user's balance is insufficient for daily payments:
1. The system attempts to use bonus funds first
2. If both bonus and main balances are insufficient, services are suspended
3. Users receive notifications about the suspension
4. Services are automatically restored when balance is replenished

### Subscription Downgrades
When users reduce their campaign count:
1. The system recalculates the monthly cost based on the new tier
2. Daily deductions are adjusted accordingly
3. No service interruption occurs during downgrades

### Billing Cycles
The system processes payments daily at midnight:
1. Campaign count is checked for each active shop
2. Daily cost is calculated and deducted
3. Payment records are created in the database
4. Subscription status is updated

Recovery procedures include:
- Automated service restoration when balance is replenished
- Notification system for payment failures
- Manual intervention options for administrators

```mermaid
sequenceDiagram
participant System as "Subscription System"
participant User as "User"
participant Admin as "Administrator"
System->>System : Daily payment processing
System->>System : Insufficient funds detected
System->>User : Send payment failure notification
User->>User : Replenish balance
User->>System : Balance top-up
System->>System : Verify sufficient funds
System->>System : Restore services
System->>User : Send service restoration notification
alt Manual intervention needed
User->>Admin : Request assistance
Admin->>System : Manual service activation
System->>User : Restore services
end
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L45-L120)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L100-L130)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L45-L120)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L100-L130)

## Performance Considerations
The subscription management system is designed to handle batch processing efficiently, particularly for daily payment processing across multiple shops.

Key performance optimizations include:
- Asynchronous database operations to prevent blocking
- Batch processing of payment calculations
- Efficient querying with proper indexing
- Connection pooling for database access

The system processes payments in a single daily batch rather than individual transactions, reducing database load and improving overall performance. The implementation uses async/await patterns to handle multiple shops concurrently without blocking operations.

```mermaid
flowchart TD
A["Start Batch Processing"] --> B["Retrieve All Active Shops"]
B --> C["Process Each Shop Concurrently"]
C --> D["Calculate Campaign Count"]
D --> E["Determine Pricing Tier"]
E --> F["Calculate Daily Cost"]
F --> G["Check Balance Availability"]
G --> |Sufficient| H["Process Payment"]
G --> |Insufficient| I["Suspend Services"]
H --> J["Record Payment Transaction"]
I --> K["Send Notification"]
J --> L["Update Subscription Status"]
K --> L
L --> M{"All Shops Processed?"}
M --> |No| C
M --> |Yes| N["Complete Batch Processing"]
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L45-L120)
- [settings_master.py](file://app/settings/settings_master.py#L300-L350)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L45-L120)
- [settings_master.py](file://app/settings/settings_master.py#L300-L350)