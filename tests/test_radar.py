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

if __name__=='__main__':unittest.main()
