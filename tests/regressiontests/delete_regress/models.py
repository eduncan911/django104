from django.conf import settings
from django.db import models, backend, connection, transaction
from django.db.models import sql, query
from django.test import TestCase

class Book(models.Model):
    pagecount = models.IntegerField()

# Can't run this test under SQLite, because you can't
# get two connections to an in-memory database.
if settings.DATABASE_ENGINE != 'sqlite3':
    class DeleteLockingTest(TestCase):
        def setUp(self):
            # Create a second connection to the database
            self.conn2 = backend.DatabaseWrapper(**settings.DATABASE_OPTIONS)

            # Put both DB connections into managed transaction mode
            transaction.enter_transaction_management()
            transaction.managed(True)
            # self.conn2._enter_transaction_management(True)

        def tearDown(self):
            # Close down the second connection.
            transaction.leave_transaction_management()
            self.conn2.close()

        def test_concurrent_delete(self):
            "Deletes on concurrent transactions don't collide and lock the database. Regression for #9479"

            # Create some dummy data
            b1 = Book(id=1, pagecount=100)
            b2 = Book(id=2, pagecount=200)
            b3 = Book(id=3, pagecount=300)
            b1.save()
            b2.save()
            b3.save()

            transaction.commit()

            self.assertEquals(3, Book.objects.count())

            # Delete something using connection 2.
            cursor2 = self.conn2.cursor()
            cursor2.execute('DELETE from delete_regress_book WHERE id=1')
            self.conn2._commit();

            # Now perform a queryset delete that covers the object
            # deleted in connection 2. This causes an infinite loop
            # under MySQL InnoDB unless we keep track of already
            # deleted objects.
            Book.objects.filter(pagecount__lt=250).delete()
            transaction.commit()
            self.assertEquals(1, Book.objects.count())
