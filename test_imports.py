from app.payments.db.models import Payment
from app.paymaster.utils.db.models import Payment as PaymasterPayment

print('Импорт успешен')
print(f'Payment.__tablename__: {Payment.__tablename__}')
print(f'PaymasterPayment.__tablename__: {PaymasterPayment.__tablename__}') 