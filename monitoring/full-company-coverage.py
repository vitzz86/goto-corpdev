#!/usr/bin/env python3
"""Finish direct monthly searches for every registry row, then resolve capped windows."""
import argparse, collections, importlib.util, json, subprocess, sys, urllib.parse
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('refresh',HERE/'refresh.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def export_companies(registry,state,tasks,start,through,output):
    baseline=[t for t in tasks if t['kind']=='entity' and not t.get('parentId') and not t.get('officialFallback')]
    localized=[t for t in m.make_tasks(registry,start,through) if t.get('searchPurpose')=='Local-language coverage']
    attempts=state['attempts'];byparent=collections.defaultdict(list)
    for t in tasks:
        if t.get('parentId'):byparent[t['parentId']].append(t)
    def leaves(job):
        children=byparent.get(job['id'],[])
        return [leaf for c in children for leaf in leaves(c)] if children else [job]
    def descendants(job):
        return [job]+[node for child in byparent.get(job['id'],[]) for node in descendants(child)]
    records=collections.defaultdict(dict)
    for r in state['records'].values():
        if not r.get('eligibleTaskIds'):continue
        for key in r['entityKeys']:records[key][r['id']]=r
    dossiers=[]
    for entity in registry['entities']:
        jobs=[t for t in baseline if t['key']==entity['key']];monthly=[]
        for job in jobs:
            leaf=leaves(job);all_windows=descendants(job);saved=attempts.get(job['id'],{})
            missing=sum(t['id'] not in attempts for t in all_windows)
            blocked=sum(attempts.get(t['id'],{}).get('status')=='source-unavailable' for t in all_windows)
            capped=sum(attempts.get(t['id'],{}).get('status')=='capped' for t in all_windows)
            tids={t['id'] for t in descendants(job)}
            found={r['id'] for r in records[entity['key']].values() if tids.intersection(r.get('eligibleTaskIds',[]))}
            status='not-checked' if not saved else 'refinement-pending' if missing else 'source-unavailable' if blocked else 'feed-cap-unresolved' if capped else 'candidates-found' if found else 'searched-no-relevant-leads'
            monthly.append(dict(month=job['start'][:7],fromDate=job['start'],through=job['through'],status=status,queryCount=len(all_windows),checkedQueries=len(all_windows)-missing,candidateRecords=len(found),blockedQueries=blocked,unresolvedDailyCaps=capped,checkedAt=max((attempts.get(t['id'],{}).get('checkedAt','') for t in all_windows),default='')))
        rs=sorted(records[entity['key']].values(),key=lambda r:(r['date'],r['title']),reverse=True)
        fallback=[(t,attempts.get(t['id'])) for t in tasks if t.get('officialFallback') and t['key']==entity['key']]
        dossier={k:entity[k] for k in ['key','id','name','registry','segment','services','markets','website','identityGuard','registryEvidence']}
        dossier.update(fromDate=start,through=through,months=monthly,baseMonthsAttempted=sum(t['id'] in attempts for t in jobs),expectedMonths=len(jobs),
            candidateRecords=len(rs),status='Not fully checked' if any(x['status']=='not-checked' for x in monthly) else 'Refinement outstanding' if any(x['status']=='refinement-pending' for x in monthly) else 'Access or feed limit unresolved' if any(x['status'] in ('source-unavailable','daily-cap-unresolved','feed-cap-unresolved') for x in monthly) else 'Candidates await source review' if rs else 'Searched; no relevant indexed lead',
            officialSiteSearches=[dict(url=t['url'],status=a.get('status') if a else 'not-checked',checkedAt=a.get('checkedAt') if a else None) for t,a in fallback],
            recentHeadlines=[dict(id=r['id'],date=r['date'],title=r['title'],publisher=r.get('sourceName',''),url=r['url'],reviewed=False) for r in rs[:20]],
            recordMeaning='Headline candidates, not verified events. A zero search result does not establish that this business had no updates.')
        language_jobs=[t for t in localized if t['key']==entity['key']]
        dossier['languageCoverage']=[dict(language='English',plannedMonths=len(jobs),checkedMonths=sum(t['id'] in attempts for t in jobs))]
        for language in sorted({t['language'] for t in language_jobs}):
            selected=[t for t in language_jobs if t['language']==language]
            dossier['languageCoverage'].append(dict(language=language,market=selected[0].get('market'),plannedMonths=len(selected),checkedMonths=sum(t['id'] in attempts for t in selected)))
        dossiers.append(dossier)
    report=dict(asOf=state.get('updatedAt'),fromDate=start,through=through,registryRows=len(dossiers),distinctRegistryKeys=len({d['key'] for d in dossiers}),
        expectedCompanyMonths=len(baseline),attemptedCompanyMonths=sum(t['id'] in attempts for t in baseline),
        companiesWithAllMonthsAttempted=sum(d['baseMonthsAttempted']==d['expectedMonths'] for d in dossiers),
        companiesWithCandidates=sum(d['candidateRecords']>0 for d in dossiers),
        companiesWithoutIndexedCandidates=sum(d['candidateRecords']==0 for d in dossiers),
        expectedLocalLanguageChecks=len(localized),attemptedLocalLanguageChecks=sum(t['id'] in attempts for t in localized),
        statusCounts=dict(collections.Counter(d['status'] for d in dossiers)),
        caveat=f"{len(dossiers)} overlapping company, brand and product registry rows; not distinct legal entities. Search completion is not proof of exhaustive event coverage.",companies=dossiers)
    (output/'company-coverage.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--from',dest='start',default='2026-01-01');ap.add_argument('--through',required=True);ap.add_argument('--output',type=Path,default=HERE/'results');ap.add_argument('--workers',type=int,default=6);ap.add_argument('--export-only',action='store_true');args=ap.parse_args()
    reg=json.loads((HERE/'registry.json').read_text());statepath=args.output/'state.json'
    def current():return m.read(statepath,{'attempts':{},'records':{},'extraTasks':[]})
    def all_tasks(state):return list({t['id']:t for t in m.make_tasks(reg,args.start,args.through)+state.get('extraTasks',[])}.values())
    def collect(extra):
        command=[sys.executable,str(HERE/'refresh.py'),'--from',args.start,'--through',args.through,'--kind','entity','--balanced-months','--workers',str(args.workers),'--limit','500','--output',str(args.output)]+extra
        subprocess.run(command,check=True)
    if not args.export_only:
        while True:
            state=current();pending=[t for t in all_tasks(state) if t['kind']=='entity' and not t.get('parentId') and t['id'] not in state['attempts']]
            if not pending:break
            print(f'BASELINE: {len(pending)} monthly company searches remain',flush=True);collect(['--baseline-only','--unsearched-only'])
            updated=current();export_companies(reg,updated,all_tasks(updated),args.start,args.through,args.output)
        # Resolve every generated entity refinement, including newly generated daily windows.
        # Never loop successful baseline checks merely to fill a request budget.
        while True:
            state=current();pending=[t for t in all_tasks(state) if t['kind']=='entity' and t['id'] not in state['attempts']]
            if not pending:break
            print(f'REFINEMENT: {len(pending)} narrower company searches remain',flush=True);collect(['--unsearched-only'])
            updated=current();export_companies(reg,updated,all_tasks(updated),args.start,args.through,args.output)
    state=current();tasks=all_tasks(state);args.output.mkdir(parents=True,exist_ok=True)
    report=export_companies(reg,state,tasks,args.start,args.through,args.output)
    print(json.dumps({k:v for k,v in report.items() if k!='companies'},indent=2))
    if not args.export_only and report['companiesWithAllMonthsAttempted']!=len(reg['entities']):raise RuntimeError('Not every registry row has all monthly checks')
if __name__=='__main__':main()
