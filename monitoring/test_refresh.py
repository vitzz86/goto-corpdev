import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('refresh',Path(__file__).with_name('refresh.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REG=json.loads(Path(__file__).with_name('registry.json').read_text())
class MonitoringTests(unittest.TestCase):
    def test_registry_and_no_unverified_feed_claim(self):
        self.assertEqual((len(REG['sources']),len(REG['entities']),len(REG['topics']),len(REG['macro'])),(93,358,44,57))
        self.assertEqual(len(m.GLOBAL.PUBLISHERS),40)
        self.assertIsNone(next(p[2] for p in m.GLOBAL.PUBLISHERS if p[0]=='Reuters'))
    def test_calendar_query_removes_rolling_window(self):
        url=m.search_url('https://news.google.com/rss/search?hl=id&gl=ID&q=old','Jenius bank when:7d','2026-01-01','2026-01-31')
        self.assertIn('before%3A2026-02-01',url);self.assertNotIn('when',url);self.assertIn('hl=id',url)
        self.assertEqual(list(m.windows('2025-12-25','2026-02-02')),[('2025-12-25','2025-12-31'),('2026-01-01','2026-01-31'),('2026-02-01','2026-02-02')])
    def test_capped_search_splits_without_losing_days(self):
        job=m.task('entity','GB:jenius','2026-01-01','2026-01-31','https://news.google.com/rss/search?q=Jenius+bank')
        children=m.split_task(job);self.assertEqual(len(children),5)
        covered=set()
        for c in children:
            day=dt.date.fromisoformat(c['start']);last=dt.date.fromisoformat(c['through'])
            while day<=last:covered.add(day);day+=dt.timedelta(days=1)
        self.assertEqual(len(covered),31)
        daily=m.split_task(children[0]);self.assertEqual(len(daily),7);self.assertEqual(m.split_task(daily[0]),[])
    def test_html_or_malformed_entries_do_not_become_no_news(self):
        for body in (b'<html><body>Access denied</body></html>',b'<rss><channel><item><title>Missing date</title></item></channel></rss>'):
            with self.assertRaises(ValueError):m.parse_feed(body)
        self.assertEqual(m.parse_feed(b'<rss><channel></channel></rss>'),[])
    def test_namesake_quarantine_and_no_automatic_verification(self):
        entity=next(e for e in REG['entities'] if e['key']=='GB:jenius')
        job=m.task('entity','GB:jenius','2026-01-01','2026-01-31','https://example.org/feed',name='Jenius')
        rows=[dict(title='Macross Maximilian Jenius Super Valkyrie toy',url='https://example.org/toy',date='2026-01-03'),dict(title='Jenius SMBC Indonesia launches banking feature',url='https://example.org/bank?utm_source=rss',date='2026-01-04')]
        records={};self.assertEqual(m.ingest(rows,job,REG,records),1)
        record=next(iter(records.values()));self.assertFalse(record['reviewed']);self.assertFalse(record['verified']);self.assertIsNone(record['eventDate'])
        rows[1]['url']='https://example.org/bank';m.ingest(rows[1:],job,REG,records);self.assertEqual(len(records),1)
    def test_collection_retains_more_than_five_and_preserves_date_boundary(self):
        job=m.task('entity','GB:jenius','2026-01-01','2026-01-31','https://example.org/feed',name='Jenius')
        rows=[dict(title=f'Jenius SMBC Indonesia banking update {i}',url=f'https://example.org/news/{i}',date='2026-01-15') for i in range(12)]
        rows.append(dict(title='Jenius SMBC Indonesia future update',url='https://example.org/future',date='2026-02-01'))
        records={};self.assertEqual(m.ingest(rows,job,REG,records),12);self.assertEqual(len(records),12)
    def test_retry_and_fair_queue_do_not_hide_failures(self):
        now=dt.datetime.now(dt.timezone.utc);tasks=m.make_tasks(REG,'2026-01-01','2026-10-18')
        jobs=m.choose(tasks,{},now,'2026-10-18',6,'all');self.assertEqual({j['kind'] for j in jobs},{'entity','topic','publisher','feed'})
        ledger={jobs[0]['id']:dict(status='source-unavailable',checkedAt=(now-dt.timedelta(hours=2)).isoformat())}
        self.assertTrue(m.due(jobs[0],ledger,now,'2026-10-18'))
        ledger[jobs[0]['id']]['checkedAt']=now.isoformat();self.assertFalse(m.due(jobs[0],ledger,now,'2026-10-18'))
    def test_balanced_queue_reaches_every_month_and_subject_family(self):
        tasks=m.make_tasks(REG,'2026-01-01','2026-10-18')
        jobs=m.choose_balanced(tasks,{},dt.datetime.now(dt.timezone.utc),'2026-10-18',200,'all')
        for family in ('entity','topic','publisher'):
            self.assertEqual({j['start'][:7] for j in jobs if j['kind']==family},{f'2026-{n:02d}' for n in range(1,11)})
        publisher_domains={j['key'].rsplit(':',1)[0] for j in jobs if j['kind']=='publisher'}
        self.assertTrue({'reuters.com','bloomberg.com'}.issubset(publisher_domains))
    def test_nested_split_coverage_and_baseline_are_not_completion(self):
        parent=m.task('entity','GB:jenius','2026-01-01','2026-01-31','https://news.google.com/rss/search?q=Jenius',name='Jenius')
        children=m.split_task(parent);grandchildren=m.split_task(children[0]);tasks=[parent]+children+grandchildren
        ledger={t['id']:dict(status='searched-no-leads',checkedAt='2026-10-18T00:00:00+00:00') for t in tasks}
        ledger[parent['id']]['status']='split';ledger[children[0]['id']]['status']='split'
        row=m.coverage(REG,tasks,ledger,{})[0];self.assertEqual(row['unresolvedSplitWindows'],0);self.assertEqual(row['editorialStatus'],'Needs primary review')
if __name__=='__main__':unittest.main()
