class FBS_Order:
    def __init__(self, data):
        self.id = data.get('id')
        self.rid = data.get('rid')
        self.created_at = data.get('createdAt')
        self.warehouse_id = data.get('warehouseId')
        self.offices = data.get('offices')
        self.address = data['address'] if 'address' in data else None
        self.required_meta = data.get('requiredMeta')
        self.user = data['user'] if 'user' in data else None
        self.barcode = data.get('skus')
        self.price = data.get('price')
        self.converted_price = data.get('convertedPrice')
        self.currency_code = data.get('currencyCode')
        self.converted_currency_code = data.get('convertedCurrencyCode')
        self.order_uid = data.get('orderUid')
        self.delivery_type = data.get('deliveryType')
        self.nmid = data.get('nmId')
        self.chrt_id = data.get('chrtId')
        self.offer_id= data.get('article')
        self.cargo_type = data.get('cargoType')