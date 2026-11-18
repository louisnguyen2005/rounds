"""Truy cập dữ liệu bộ sưu tập."""
from .database import Repository


class Catalog(Repository):
    database = 'catalog.sqlite3'

    def list_collections(self):
        return self.connection.execute('SELECT * FROM collections ORDER BY id')

    def collection_exists(self, parameters):
        return self.connection.execute('SELECT 1 FROM collections WHERE id=?', parameters)

    def create_note(self, parameters):
        return self.connection.execute('INSERT INTO collection_notes(user_id,collection_id,note) VALUES(?,?,?)', parameters)

    def list_customer_notes(self, parameters):
        return self.connection.execute('SELECT n.id,c.title FROM collection_notes n JOIN collections c ON c.id=n.collection_id WHERE n.user_id=? ORDER BY n.id DESC', parameters)

    def list_collection_options(self):
        return self.connection.execute('SELECT id,title FROM collections ORDER BY id')

    def find_note(self, parameters):
        return self.connection.execute('SELECT n.*,c.title FROM collection_notes n JOIN collections c ON c.id=n.collection_id WHERE n.id=?', parameters)

    def search(self, q, patched):
        if patched:
            sql = "SELECT id,title,description FROM collections WHERE title LIKE ?"
            rows = self.connection.execute(sql, ("%" + q + "%",)).fetchall()
        else:
            sql = "SELECT id,title,description FROM collections WHERE title LIKE '%" + q + "%'"
            rows = self.connection.execute(sql).fetchall()
        return rows
