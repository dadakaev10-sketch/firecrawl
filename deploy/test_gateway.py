import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path
spec = importlib.util.spec_from_file_location('gateway', Path(__file__).with_name('gateway.py'))
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

class SafetyTests(unittest.TestCase):
    def test_private_destinations_and_dns(self):
        for address in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', 'fc00::1', '::ffff:127.0.0.1']:
            with self.subTest(address=address), patch.object(gateway.socket, 'getaddrinfo', return_value=[(0,0,0,'',(address,443))]):
                with self.assertRaises(ValueError): gateway.public_url('https://example.org')
    def test_protocol_credentials_ports(self):
        for url in ['file:///etc/passwd','http://name:password@example.org','http://example.org:3002']:
            with self.assertRaises(ValueError): gateway.public_url(url)
    def test_clamps_and_discards_unsafe_scrape_options(self):
        with patch.object(gateway.socket, 'getaddrinfo', return_value=[(0,0,0,'',('93.184.216.34',443))]):
            body = gateway.crawl_body({'url':'https://example.org','limit':50,'scrapeOptions':{'skipTlsVerification':True}})
            self.assertEqual(body['limit'],25)
            self.assertEqual(body['maxDepth'],2)
            self.assertEqual(body['scrapeOptions'],{'formats':['markdown'],'timeout':30000})
    def test_invalid_limits_and_extra_fields(self):
        for limit in [True,0,-1,1001,1.5,'25']:
            with self.assertRaises(ValueError): gateway.crawl_body({'url':'https://example.org','limit':limit})
        with self.assertRaises(ValueError): gateway.crawl_body({'url':'https://example.org','webhook':'http://localhost'})

if __name__ == '__main__': unittest.main()
