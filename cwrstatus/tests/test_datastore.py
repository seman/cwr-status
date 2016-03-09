import json

from mock import patch
from cwrstatus.datastore import (
    Datastore,
    S3,
)
from cwrstatus.testing import (
    DatastoreTest,
    TestCase,
    make_build_info
)


class TestDatastore(DatastoreTest):

    def test_get(self):
        doc = self.make_doc()
        self.update_data(doc)
        ds = Datastore()
        items = list(ds.get())
        self.assertEqual(items, [doc])

    def test_get_multiple(self):
        doc = self.make_doc()
        doc2 = self.make_doc(2)
        self.update_data(doc)
        self.update_data(doc2)
        ds = Datastore()
        items = list(ds.get())
        self.assertEqual(items[0], doc2)
        self.assertEqual(items[1], doc)

    def test_get_filter(self):
        doc = self.make_doc()
        doc2 = self.make_doc(2)
        self.update_data(doc)
        self.update_data(doc2)
        ds = Datastore()
        items = list(ds.get(filter={'_id': doc['_id']}))
        self.assertEqual(items, [doc])

    def test_get_limit(self):
        doc = self.make_doc(1)
        doc2 = self.make_doc(2)
        doc3 = self.make_doc(3)
        self.update_data(doc)
        self.update_data(doc2)
        self.update_data(doc3)
        ds = Datastore()
        items = list(ds.get(limit=2))
        self.assertEqual(items, [doc3, doc2])

    def test_get_skip(self):
        doc = self.make_doc(1)
        doc2 = self.make_doc(2)
        doc3 = self.make_doc(3)
        self.update_data(doc)
        self.update_data(doc2)
        self.update_data(doc3)
        ds = Datastore()
        items = list(ds.get(skip=1))
        self.assertEqual(items, [doc2, doc])

    def test_get_one(self):
        doc = self.make_doc()
        doc2 = self.make_doc(2)
        self.update_data(doc)
        self.update_data(doc2)
        ds = Datastore()
        item = ds.get_one(filter={'_id': doc['_id']})
        self.assertEqual(item, doc)

    def test_get_by_bundle_name(self):
        doc = self.make_doc(1)
        doc2 = self.make_doc(2)
        self.update_data(doc)
        self.update_data(doc2)
        ds = Datastore()
        items = list(ds.get_by_bundle_name(doc['bundle_name']))
        self.assertEqual(items, [doc])

    def test_update(self):
        doc = self.make_doc()
        ds = Datastore()
        with patch('cwrstatus.datastore.get_current_utc_time', autospec=True,
                   return_value=doc['_updated_on']) as gcut_mock:
            ds.update({"_id": doc["_id"]}, doc)
        items = list(self.ds.db.cwr.find())
        self.assertEqual(items, [doc])
        gcut_mock.assert_called_once_with()

    def test_update_existing_doc(self):
        doc = self.make_doc()
        ds = Datastore()
        with patch('cwrstatus.datastore.get_current_utc_time', autospec=True,
                   return_value=doc['_updated_on']):
            ds.update({"_id": doc["_id"]}, doc)
            items = list(self.ds.db.cwr.find())
            self.assertEqual(items, [doc])

            doc['bundle_name'] = 'new bundle'
            ds.update({"_id": doc["_id"]}, doc)
            items = list(self.ds.db.cwr.find())
            self.assertEqual(items, [doc])

    def test_update_and_get(self):
        doc = self.make_doc()
        ds = Datastore()
        with patch('cwrstatus.datastore.get_current_utc_time', autospec=True,
                   return_value=doc['_updated_on']) as gcut_mock:
            ds.update({"_id": doc["_id"]}, doc)
        items = list(ds.get())
        self.assertEqual(items, [doc])
        gcut_mock.assert_called_once_with()

    def update_data(self, doc):
        self.ds.db.cwr.update({'_id': doc['_id']}, doc, upsert=True)

    def make_doc(self, count=1):
        count = str(count)
        return {
            'bundle_name': 'openstack' + count,
            '_id': 'foo' + count,
            '_updated_on': count}


class TestS3(TestCase):

    def test_factory(self):
        cred = ('fake_user', 'fake_pass')
        s3conn_cxt = patch(
            'cwrstatus.datastore.S3Connection', autospec=True)
        with s3conn_cxt as j_mock:
            with patch('cwrstatus.datastore.get_s3_access',
                       return_value=cred, autospec=True) as g_mock:
                s3 = S3.factory('cwr', 'dir')
                self.assertTrue(isinstance(s3, S3))
                self.assertEqual(s3.dir, 'dir')
                self.assertEqual(('cwr',), j_mock.mock_calls[1][1])
                s3.dir = 'new/dir'
                self.assertEqual(s3.dir, 'new/dir')
        g_mock.assert_called_once_with()
        j_mock.assert_called_once_with(cred[0], cred[1])

    def test_list(self):
        fb = FakeBucket()
        s3 = S3('cwr', None, None, None, fb)
        all_list = list(s3.list())
        self.assertItemsEqual(
            [x.name for x in all_list],
            [x.name for x in make_bucket_list() if x.name != 'cwr/'])

    def test_list_do_not_skip_folder(self):
        fb = FakeBucket()
        s3 = S3('cwr', None, None, None, fb)
        all_list = list(s3.list(skip_folder=False))
        self.assertItemsEqual(
            [x.name for x in all_list],
            [x.name for x in make_bucket_list()])

    def filter_fun(self, value):
        return value.endswith('result.json')

    def test_list_filter(self):
        fb = FakeBucket()
        s3 = S3('cwr', None, None, None, fb)
        all_list = list(s3.list(filter_fun=self.filter_fun))
        self.assertItemsEqual(
            [x.name for x in all_list],
            [x.name for x in make_bucket_list()
             if self.filter_fun(x.name)])


def make_bucket_list():
    keys = [FakeKey('cwr/'),
            FakeKey('cwr/cwr-test/1/1234-result-results.json'),
            FakeKey('cwr/cwr-test/1/1234-log-git-result.json'),
            FakeKey('cwr/cwr-test/1/1234-log-git-result.svg'),
            FakeKey('cwr/cwr-test/2/5679-result-results.json'),
            FakeKey('cwr/cwr-test/2/5678-log-git-result.json'),
            FakeKey('cwr/cwr-test/2/5678-log-git-result.svg')]
    return keys


class FakeKey:

    def __init__(self, name):
        self.name = name
        self.etag = 'AB123'

    def get_contents_as_string(self):
        return json.dumps(make_build_info())


class FakeBucket:

    def list(self, path=None):
        for l in make_bucket_list():
            yield l

    def get_key(self, path):
        return FakeKey('cwr/cwr-test/1/1234-result-results.json')
