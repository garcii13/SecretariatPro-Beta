"""Disposable Manager UI preview with synthetic sporting data, never a real account."""
import json,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import Mock
from secretariat_core.exchange.client import ExchangeClient
from tests.test_federation_exchange import catalog,FederationTests
import uvicorn
with tempfile.TemporaryDirectory(prefix='secretariat-federation-ui-') as folder:
 os.environ['SP_EXCHANGE_CACHE']=str(Path(folder)/'cache.sqlite')
 os.environ['UI_PREVIEW_SECRET']='disposable-secret-with-at-least-32-characters'
 os.environ['SP_FEDERATION_CONNECTIONS']=json.dumps([{'id':'preview','enabled':True,'workspaceId':'ws','namespace':'fed.test','competitionId':'c','url':'http://127.0.0.1:5435','clientId':'preview','secretEnv':'UI_PREVIEW_SECRET','modules':['catalog','captures','statistics']}])
 e=ExchangeClient('http://127.0.0.1:5435','preview',os.environ['UI_PREVIEW_SECRET'],'fed.test','c',os.environ['SP_EXCHANGE_CACHE']);e.request=Mock(return_value=catalog());e.bootstrap();e.close()
 client,db=FederationTests().client()
 client.manager_dashboard_counts.return_value={'competitions':1,'teams':2,'players':4,'matches':2}
 client.manager_list_matches.return_value=[]
 from manager_api import main
 main.runtime.require_connected=lambda:client
 main.runtime.require_write=lambda:client
 main.runtime.state=lambda:{'connected':True,'profile':{'display_name':'Pruebas de integración','email':'preview@example.test'},'workspaces':[{'id':'ws','name':'Espacio de pruebas'}],'workspace':{'id':'ws','name':'Espacio de pruebas','role':'owner'},'subscription':{},'access':{'allowed':True,'entitlements':{}},'permissions':{'write_allowed':True,'can_manage':True},'application':{'version':'Vista de prueba','build':'Sports Exchange'}}
 uvicorn.run(main.app,host='127.0.0.1',port=8784,log_level='warning')
