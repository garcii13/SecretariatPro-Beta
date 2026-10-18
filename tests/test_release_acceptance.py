import copy
from pathlib import Path
import runpy
import unittest

gate = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'packaging/verify_acceptance.py'))


class ReleaseAcceptanceTests(unittest.TestCase):
    def test_requires_real_checks_for_each_build_and_exact_installer_hashes(self):
        commits={'windows-2022':'a'*40,'macos-15':'b'*40}
        hashes={platform:{platform+'.installer':'c'*64} for platform in commits}
        evidence={'version':'1.0.0-beta.11','reviewer':'Tester','checked_at':'2026-10-18',
                  'cloud':dict.fromkeys(gate['CLOUD_CHECKS'],True),
                  'platforms':{platform:{'commit':commit,'artifacts':hashes[platform],
                    **dict.fromkeys(gate['CHECKS'],True)} for platform,commit in commits.items()}}
        validate=lambda value:gate['validate_acceptance'](value,'1.0.0-beta.11',commits,hashes)
        self.assertTrue(validate(evidence))
        for change in ('missing','skipped','string','commit','hash','cloud'):
            value=copy.deepcopy(evidence)
            if change=='missing':value['platforms'].pop('windows-2022')
            elif change=='skipped':value['platforms']['macos-15']['camera_ocr']=False
            elif change=='string':value['platforms']['macos-15']['visual']='true'
            elif change=='commit':value['platforms']['macos-15']['commit']='d'*40
            elif change=='hash':value['platforms']['macos-15']['artifacts']={'other':'c'*64}
            else:value['cloud']['tenant_isolation']=False
            with self.subTest(change=change),self.assertRaises(ValueError):validate(value)
