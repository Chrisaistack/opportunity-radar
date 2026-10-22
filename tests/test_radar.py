import unittest
import io
import json
import urllib.error
import urllib.parse
from unittest.mock import patch
from radar import fetch
from radar import analyse
class RadarTests(unittest.TestCase):
    def test_commercial_signal(self):
        result=analyse({'description':'Commercial warehouse roof repairs','entity':'42'})
        self.assertIn('roofing',result['trade_matches'])
        self.assertTrue(result['source_url'].endswith('/42'))
    def test_irrelevant(self):
        self.assertIsNone(analyse({'description':'New garden fence'}))
    def test_escapes_html(self):
        from radar import render
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.html'
            x=analyse({'description':'<script>alert(1)</script> roof industrial','entity':'5'})
            render([x],p,'2026-10-01',False)
            self.assertNotIn('<script>',p.read_text())
class FetchTests(unittest.TestCase):
    def response(self, records):
        return io.StringIO(json.dumps({'entities': records}))

    @patch('radar.time.sleep')
    @patch('radar.urllib.request.urlopen')
    def test_pagination_and_date_filter(self, open_url, sleep):
        open_url.side_effect = [self.response([{'entity': i} for i in range(100)]),
                                self.response([{'entity': 100}])]
        self.assertEqual(len(fetch('2026-10-01', 101)), 101)
        urls = [urllib.parse.parse_qs(call.args[0].full_url.split('?')[1])
                for call in open_url.call_args_list]
        self.assertEqual(urls[0]['start_date_match'], ['since'])
        self.assertEqual(urls[0]['start_date_month'], ['10'])
        self.assertEqual(urls[1]['offset'], ['100'])
        self.assertEqual(urls[1]['limit'], ['1'])

    @patch('radar.urllib.request.urlopen')
    def test_empty_page_is_valid(self, open_url):
        open_url.return_value = self.response([])
        self.assertEqual(fetch('2026-10-01', 100), [])

    @patch('radar.urllib.request.urlopen')
    def test_bad_response_fails(self, open_url):
        for payload in ({}, {'entities': None}, {'entities': ['wrong']}, []):
            with self.subTest(payload=payload):
                open_url.return_value = io.StringIO(json.dumps(payload))
                with self.assertRaises(ValueError):
                    fetch('2026-10-01', 100)

    @patch('radar.urllib.request.urlopen')
    def test_api_error_is_not_demo_or_empty_success(self, open_url):
        open_url.side_effect = urllib.error.URLError('offline')
        with self.assertRaises(urllib.error.URLError):
            fetch('2026-10-01', 100)

    @patch('radar.urllib.request.urlopen')
    def test_invalid_inputs_do_not_make_requests(self, open_url):
        for since, limit in [('bad', 100), ('2026-10-01', 0), ('2026-10-01', 1001)]:
            with self.assertRaises(ValueError):
                fetch(since, limit)
        open_url.assert_not_called()

class LondonTests(unittest.TestCase):
    def response(self, records, total=None, **extra):
        return io.StringIO(json.dumps({'hits': {'total': {'value': len(records) if total is None else total, 'relation': 'eq'},
                                              'hits': [{'_source': r} for r in records]}, **extra}))

    def record(self, identity='Camden-1'):
        return {'id': identity, 'lpa_app_no': '2026/1/P', 'description': 'Warehouse roof replacement',
                'valid_date': '21/10/2026', 'lpa_name': 'Camden', 'status': 'Application Received',
                'url_planning_app': 'https://example.gov.uk/planning/1'}

    @patch('radar.urllib.request.urlopen')
    def test_maps_real_fields_and_preserves_council_link(self, open_url):
        from radar import fetch_london
        open_url.return_value = self.response([self.record()])
        records, total = fetch_london('2026-10-01', 100)
        item = analyse(records[0])
        self.assertEqual(total, 1)
        self.assertEqual(item['submitted'], '2026-10-21')
        self.assertEqual(item['borough'], 'Camden')
        self.assertEqual(item['application_status'], 'Application Received')
        self.assertEqual(item['source_url'], 'https://example.gov.uk/planning/1')
        query = json.loads(open_url.call_args.args[0].data)
        self.assertEqual(query['query']['range']['valid_date']['gte'], '01/10/2026')
        self.assertNotIn('site_number', query['_source'])

    @patch('radar.time.sleep')
    @patch('radar.urllib.request.urlopen')
    def test_paginates_and_deduplicates(self, open_url, sleep):
        from radar import fetch_london
        open_url.side_effect = [self.response([self.record(str(i)) for i in range(100)], 101),
                                self.response([self.record('0')], 101)]
        records, total = fetch_london('2026-10-01', 101)
        self.assertEqual(len(records), 100)
        self.assertEqual(total, 101)
        self.assertEqual(json.loads(open_url.call_args.args[0].data)['from'], 100)

    @patch('radar.urllib.request.urlopen')
    def test_missing_description_is_explicitly_empty(self, open_url):
        from radar import fetch_london
        rec = self.record(); rec['description'] = None
        open_url.return_value = self.response([rec])
        records, _ = fetch_london('2026-10-01', 100)
        self.assertEqual(records[0]['description'], '')
        self.assertIsNone(analyse(records[0]))

    @patch('radar.urllib.request.urlopen')
    def test_empty_or_partial_feed_fails(self, open_url):
        from radar import fetch_london
        for extra in ({}, {'timed_out': True}, {'_shards': {'failed': 1}}):
            open_url.return_value = self.response([], **extra)
            with self.assertRaises(ValueError):
                fetch_london('2026-10-01', 100)

    @patch('radar.urllib.request.urlopen')
    def test_rejects_out_of_range_dates(self, open_url):
        from radar import fetch_london
        rec = self.record(); rec['valid_date'] = '01/01/2020'
        open_url.return_value = self.response([rec])
        with self.assertRaises(ValueError):
            fetch_london('2026-10-01', 100)

    def test_unsafe_source_url_not_rendered(self):
        result = analyse({'description': 'roof work', 'source_url': 'javascript:alert(1)'})
        self.assertTrue(result['source_url'].startswith('https://'))

if __name__=='__main__':unittest.main()
