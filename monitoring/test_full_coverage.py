import importlib.util,json,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('full_coverage',HERE/'full-company-coverage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REG=json.loads((HERE/'registry.json').read_text())
class FullCoverageTests(unittest.TestCase):
 def test_all_entries_exist_even_without_a_single_news_result(self):
  tasks=m.m.make_tasks(REG,'2026-01-01','2026-10-18');state={'attempts':{},'records':{}}
  with tempfile.TemporaryDirectory() as output:
   report=m.export_companies(REG,state,tasks,'2026-01-01','2026-10-18',Path(output))
  self.assertEqual(report['registryRows'],len(REG['entities']));self.assertEqual(report['distinctRegistryKeys'],len(REG['entities']));self.assertEqual(report['expectedCompanyMonths'],len(REG['entities'])*10)
  self.assertEqual(report['companiesWithAllMonthsAttempted'],0);self.assertEqual(report['companiesWithoutIndexedCandidates'],len(REG['entities']))
  self.assertTrue(all(len(c['months'])==10 and c['status']=='Not fully checked' for c in report['companies']))
 def test_all_attempts_are_not_mislabelled_as_verified_news(self):
  tasks=m.m.make_tasks(REG,'2026-01-01','2026-10-18');jobs=[t for t in tasks if t['kind']=='entity'];state={'attempts':{t['id']:{'status':'searched-no-leads','checkedAt':'2026-10-18T00:00:00+00:00'} for t in jobs},'records':{}}
  with tempfile.TemporaryDirectory() as output:report=m.export_companies(REG,state,tasks,'2026-01-01','2026-10-18',Path(output))
  self.assertEqual(report['attemptedCompanyMonths'],len(REG['entities'])*10);self.assertEqual(report['companiesWithAllMonthsAttempted'],len(REG['entities']));self.assertEqual(report['companiesWithCandidates'],0)
  self.assertTrue(all(c['status']=='Searched; no relevant indexed lead' and not c['recentHeadlines'] for c in report['companies']))
 def test_failed_search_stays_visible(self):
  tasks=m.m.make_tasks(REG,'2026-01-01','2026-10-18');jobs=[t for t in tasks if t['kind']=='entity'];attempts={t['id']:{'status':'searched-no-leads','checkedAt':'2026-10-18T00:00:00+00:00'} for t in jobs};attempts[jobs[0]['id']]['status']='source-unavailable'
  with tempfile.TemporaryDirectory() as output:report=m.export_companies(REG,{'attempts':attempts,'records':{}},tasks,'2026-01-01','2026-10-18',Path(output))
  c=next(c for c in report['companies'] if c['key']==jobs[0]['key']);self.assertEqual(c['months'][0]['status'],'source-unavailable');self.assertEqual(c['status'],'Access or feed limit unresolved')
if __name__=='__main__':unittest.main()
