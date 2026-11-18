"""Truy cập dữ liệu cửa hàng."""
from .database import Repository


class Shop(Repository):
    database = 'shop.sqlite3'

    def find_customer(self, parameters):
        return self.connection.execute('SELECT * FROM customers WHERE id=?', parameters)

    def list_products(self):
        return self.connection.execute('SELECT * FROM products ORDER BY id')

    def find_product(self, parameters):
        return self.connection.execute('SELECT * FROM products WHERE id=?', parameters)

    def ping(self):
        return self.connection.execute('SELECT 1')

    def create_customer(self, parameters):
        return self.connection.execute("INSERT INTO customers(username,password,name,email,address,rank) VALUES(?,?,?,?,?, 'basic')", parameters)

    def find_customer_by_username(self, parameters):
        return self.connection.execute('SELECT * FROM customers WHERE username=?', parameters)

    def update_customer(self, parameters):
        return self.connection.execute('UPDATE customers SET name=?,email=?,address=? WHERE id=?', parameters)

    def list_saved_products(self, parameters):
        return self.connection.execute('SELECT p.* FROM saved_collection s JOIN products p ON p.id=s.product_id WHERE s.user_id=? ORDER BY p.id', parameters)

    def product_exists(self, parameters):
        return self.connection.execute('SELECT 1 FROM products WHERE id=?', parameters)

    def save_product(self, parameters):
        return self.connection.execute('INSERT OR IGNORE INTO saved_collection VALUES(?,?)', parameters)

    def find_product_id(self, parameters):
        return self.connection.execute('SELECT id FROM products WHERE id=?', parameters)

    def list_coupons(self):
        return self.connection.execute('SELECT * FROM coupons ORDER BY discount')

    def find_discount(self, parameters):
        return self.connection.execute('SELECT discount FROM coupons WHERE code=?', parameters)

    def create_order(self, parameters):
        return self.connection.execute("INSERT INTO orders(code,user_id,total,status,created,memo) VALUES(?,?,?,'Đang xử lý','04/11/2026',?)", parameters)

    def create_order_items(self, parameters):
        return self.connection.executemany('INSERT INTO order_items VALUES(?,?,?,?)', parameters)

    def list_customer_orders(self, parameters):
        return self.connection.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC', parameters)

    def find_order(self, parameters):
        return self.connection.execute('SELECT * FROM orders WHERE id=?', parameters)

    def list_order_items(self, parameters):
        return self.connection.execute('SELECT p.name,oi.quantity,oi.price FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?', parameters)

    def create_outfit(self, parameters):
        return self.connection.execute('INSERT INTO outfits(user_id,name,manifest) VALUES(?,?,?)', parameters)

    def list_offers(self):
        return self.connection.execute('SELECT id FROM vip_offers ORDER BY id DESC LIMIT 50')

    def find_offer(self, parameters):
        return self.connection.execute('SELECT * FROM vip_offers WHERE id=?', parameters)

    def list_reconciliations(self):
        return self.connection.execute('SELECT ref,value FROM reconciliation_notes ORDER BY id DESC LIMIT 100')

    def list_orders(self):
        return self.connection.execute('SELECT * FROM orders ORDER BY id DESC')

    def create_product(self, parameters):
        return self.connection.execute("INSERT INTO products(name,category,price,image,description) VALUES(?,?,?,'bag.svg',?)", parameters)

    def update_order_status(self, parameters):
        return self.connection.execute('UPDATE orders SET status=? WHERE id=?', parameters)

    def create_offer(self, parameters):
        return self.connection.execute('INSERT INTO vip_offers(code) VALUES(?)', parameters)

    def grant_membership(self, parameters):
        return self.connection.execute('UPDATE customers SET rank=? WHERE username=?', parameters)

    def create_reconciliation(self, parameters):
        return self.connection.execute('INSERT INTO reconciliation_notes(ref,value) VALUES(?,?)', parameters)

    def list_reconciliation_refs(self):
        return self.connection.execute('SELECT ref FROM reconciliation_notes ORDER BY id DESC LIMIT 100')
