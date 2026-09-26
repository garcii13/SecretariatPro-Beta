import socket, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from secretariat_api.lan_access import lan_addresses, listener_reachable
from secretariat_core.services.replay_library import ReplayLibrary
from supabase_client import ScoreboardSupabaseClient
from storage3.exceptions import StorageApiError

class ConnectionSampleDeletionTests(unittest.TestCase):
    def test_interfaces(self):
        def addr(ip): return NS(family=socket.AF_INET,address=ip)
        with patch('psutil.net_if_addrs',return_value={'utun1':[addr('10.1.1.1')],'lo0':[addr('127.0.0.1')],'en0':[addr('10.8.2.129')]}),patch('psutil.net_if_stats',return_value={}):
            self.assertEqual([r['address'] for r in lan_addresses()],['10.8.2.129','10.1.1.1'])
    def test_listener_failure(self):
        with patch('socket.create_connection',side_effect=ConnectionRefusedError):
            self.assertFalse(listener_reachable('10.8.2.129',8765))
    def test_delete_restore_collision(self):
        with tempfile.TemporaryDirectory() as d:
            lib=ReplayLibrary(d); video=lib.exports_dir/'goal.mp4'; video.write_bytes(b'original')
            lib.store.write({'clips':[],'highlights':[{'id':'a','match_id':'one','path':str(video)}]})
            with self.assertRaises(KeyError): lib.delete_video('a','two')
            self.assertTrue(video.exists()); lib.delete_video('a','one')
            self.assertFalse(video.exists()); self.assertEqual(lib.snapshot('one')['highlights'],[])
            with self.assertRaises(KeyError): lib.restore_video('a','two')
            video.write_bytes(b'new'); restored=lib.restore_video('a','one')
            self.assertEqual(Path(restored['path']).read_bytes(),b'original'); self.assertEqual(video.read_bytes(),b'new')
    def client(self,error=None,existing=None):
        c=object.__new__(ScoreboardSupabaseClient); c.user=NS(id='user'); c._active_workspace_id=Mock(return_value='workspace'); c.client=Mock()
        c.client.rpc.side_effect=lambda name,args:NS(execute=lambda:NS(data=existing if name=='sp_find_ocr_sample' else 'sample'))
        b=c.client.storage.from_.return_value; b.upload.side_effect=error
        return c,b
    def test_insert_only(self):
        c,b=self.client(); c.upload_ocr_sample(b'jpeg',{'field':'time'})
        self.assertEqual(b.upload.call_args.kwargs['file_options']['upsert'],'false')
    def test_duplicate_retry(self):
        c,b=self.client(StorageApiError('Already exists','Duplicate',409)); c.upload_ocr_sample(b'jpeg',{'field':'time'})
        self.assertEqual(c.client.rpc.call_args.args[0],'sp_submit_ocr_sample')
    def test_denied(self):
        c,b=self.client(StorageApiError('RLS','Forbidden',403))
        with self.assertRaises(StorageApiError): c.upload_ocr_sample(b'jpeg',{'field':'time'})
        self.assertEqual(c.client.rpc.call_count,1)
    def test_existing_skipped(self):
        c,b=self.client(existing='sample'); self.assertTrue(c.upload_ocr_sample(b'jpeg',{'field':'time'})['duplicate']); b.upload.assert_not_called()
