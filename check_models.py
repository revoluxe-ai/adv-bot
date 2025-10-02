from app.modules.billing.models import AdvPayment as AP

print(f"AP tablename: {AP.__tablename__}")

print("\nAP columns:")
for column in AP.__table__.columns:
    print(f"- {column.name}: {column.type}")

print("\nAP foreign keys:")
for fk in AP.__table__.foreign_keys:
    print(f"- {fk.column.name} -> {fk.target_fullname}")
