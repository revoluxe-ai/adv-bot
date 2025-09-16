from app.modules.common_slaves.wildberries.models import AdvPayment as AP2
from app.modules.wb_adv_updater.models import AdvPayment as AP1

print(f'AP1 tablename: {AP1.__tablename__}')
print(f'AP2 tablename: {AP2.__tablename__}')

print("\nAP1 columns:")
for column in AP1.__table__.columns:
    print(f"- {column.name}: {column.type}")

print("\nAP2 columns:")
for column in AP2.__table__.columns:
    print(f"- {column.name}: {column.type}")

print("\nAP1 foreign keys:")
for fk in AP1.__table__.foreign_keys:
    print(f"- {fk.column.name} -> {fk.target_fullname}")

print("\nAP2 foreign keys:")
for fk in AP2.__table__.foreign_keys:
    print(f"- {fk.column.name} -> {fk.target_fullname}")
