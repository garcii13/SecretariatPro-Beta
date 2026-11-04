import base64,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from secretariat_core.exchange import connections as store
from secretariat_core.exchange import federation as fed

def code(url='http://127.0.0.1:4321'):
 return 'SX1.'+base64.urlsafe_b64encode(json.dumps({'v':1,'url':url,'token':'T'*43}).encode()).decode().rstrip('=')
def info():return {'schema':'sports.exchange.v1','namespace':'test.fed','name':'Test federation','competitions':[{'id':'c','name':'Test cup','season':'2026/27'}],'scopes':['catalog:read','captures:write']}
def credential():return {**info(),'clientId':'remote-client','sourceNamespace':'urn:test:client','secret':'test-secret-with-at-least-32-characters'}

class ConnectionWizardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'SP_EXCHANGE_CACHE':str(Path(self.tmp.name)/'cache.sqlite'),'SP_FEDERATION_CONNECTIONS':'[]'});self.env.start()
  self.client=Mock();self.client.user_id='user';self.client._active_workspace_id.return_value='sandbox'
 def tearDown(self):fed.stop_worker();self.env.stop();self.tmp.cleanup()
 def preview(self):
  with patch.object(store,'remote',return_value=info()):return store.inspect(self.client,code())
 def finish(self,preview=None):
  preview=preview or self.preview()
  with patch.object(store,'remote',return_value=credential()):return store.finish(self.client,preview['ticketId'],'c')
 def test_invalid_invitation_and_unsafe_origins_rejected(self):
  for value in ['bad',code('http://169.254.169.254'),code('https://name:password@example.com'),code('https://example.com/private')]:
   with self.subTest(value=value[:10]),self.assertRaises(ValueError):store.read_code(value)
 def test_preview_exposes_names_only_and_binds_to_account_workspace(self):
  p=self.preview();self.assertEqual(p['competitions'][0]['name'],'Test cup');self.assertNotIn('secret',p);self.assertNotIn('token',p)
  self.client._active_workspace_id.return_value='existing-aeuf'
  with self.assertRaises(ValueError):self.finish(p)
  self.client._active_workspace_id.return_value='sandbox';self.client.user_id='someone-else'
  with self.assertRaises(ValueError):self.finish(p)
 def test_save_works_without_environment_changes_and_hides_credentials(self):
  result=self.finish();configs=fed.configurations('sandbox');self.assertEqual(len(configs),1);self.assertEqual(configs[0]['id'],result['id'])
  status=fed.public_status(self.client);self.assertTrue(status['connections'][0]['managed']);self.assertNotIn(credential()['secret'],json.dumps(status))
  self.assertEqual(fed.configurations('existing-aeuf'),[])
  for path in [Path(self.tmp.name)/'connection-settings.sqlite',Path(self.tmp.name)/'connection-settings.key']:
   if os.name!='nt':self.assertEqual(path.stat().st_mode&0o777,0o600)
  db=store.database();dump='\n'.join(db.iterdump());db.close();self.assertNotIn(credential()['secret'],dump);self.assertNotIn('T'*43,dump)
 def test_failed_exchange_retries_same_redemption_id(self):
  p=self.preview()
  with patch.object(store,'remote',side_effect=ValueError('offline')) as first:
   with self.assertRaises(ValueError):store.finish(self.client,p['ticketId'],'c')
  with patch.object(store,'remote',return_value=credential()) as second:store.finish(self.client,p['ticketId'],'c')
  self.assertEqual(first.call_args.args[2]['redemptionId'],second.call_args.args[2]['redemptionId'])
 def test_different_workspace_and_federation_cannot_replace_existing_connection(self):
  first=self.finish();self.client._active_workspace_id.return_value='second-sandbox';second=self.finish()
  self.assertNotEqual(first['id'],second['id']);self.assertEqual(len(fed.configurations('sandbox')),1);self.assertEqual(len(fed.configurations('second-sandbox')),1)
 def test_readonly_invitation_cannot_gain_capture(self):
  i=info();i['scopes']=['catalog:read']
  with patch.object(store,'remote',return_value=i):p=store.inspect(self.client,code())
  with self.assertRaises(PermissionError):store.finish(self.client,p['ticketId'],'c',True)
 def test_disconnect_preserves_cache_and_reconnect_tests_access(self):
  result=self.finish();store.set_enabled(self.client,result['id'],False)
  self.assertEqual(fed.configurations('sandbox'),[]);self.assertFalse(fed.public_status(self.client)['connections'][0]['enabled'])
  with patch.object(fed,'connect') as connect:
   store.set_enabled(self.client,result['id'],True);connect.return_value.pull.assert_called_once()
  self.assertEqual(len(fed.configurations('sandbox')),1)
 def test_revoked_connection_does_not_reenable_after_failed_test(self):
  result=self.finish();store.set_enabled(self.client,result['id'],False)
  with patch.object(fed,'connect') as connect:
   connect.return_value.pull.side_effect=RuntimeError('revoked')
   with self.assertRaises(RuntimeError):store.set_enabled(self.client,result['id'],True)
  self.assertEqual(fed.configurations('sandbox'),[])
 def test_federation_permission_check_applies_before_testing_code(self):
  self.client._require_competition_manager.side_effect=PermissionError('read-only')
  with patch.object(store,'remote') as remote:
   with self.assertRaises(PermissionError):store.inspect(self.client,code())
   remote.assert_not_called()
 def test_expired_ticket_is_not_redeemed(self):
  p=self.preview();db=store.database()
  with db:db.execute('UPDATE pending SET expires=0')
  db.close()
  with patch.object(store,'remote') as remote:
   with self.assertRaises(ValueError):store.finish(self.client,p['ticketId'],'c')
   remote.assert_not_called()
