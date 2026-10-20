#!/usr/bin/env python3
"""Resumable public-feed discovery and evidence queue. Never publishes facts."""
import argparse, concurrent.futures, collections, csv, datetime as dt, hashlib, importlib.util, json, re, time
import urllib.parse, urllib.request, urllib.error, xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
GLOBAL=module('global_identity',HERE/'collect-global-publisher-news.py')
LOCAL=module('local_identity',HERE/'news-relevance.py')
LANGUAGES=module('language_coverage',HERE/'language-coverage.py')

def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(value):return hashlib.sha256(value.encode()).hexdigest()[:24]
def canonical(url):return GLOBAL.canonical(url)
def read(path,default):return json.loads(path.read_text()) if path.exists() else default

def windows(start,through):
    current=dt.date.fromisoformat(start); end=dt.date.fromisoformat(through)
    while current<=end:
        next_month=(current.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
        yield current.isoformat(),min(end,next_month-dt.timedelta(days=1)).isoformat()
        current=next_month

def search_url(template,query,start,through):
    parsed=urllib.parse.urlsplit(template);values=dict(urllib.parse.parse_qsl(parsed.query))
    query=re.sub(r'\s+(?:when:|after:|before:)\S+','',query)
    before=(dt.date.fromisoformat(through)+dt.timedelta(days=1)).isoformat()
    values['q']=f'{query} after:{start} before:{before}'
    return urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urllib.parse.urlencode(values),''))

def task(kind,key,start,through,url,priority='P1',**extra):
    return dict(id=digest('|'.join([kind,key,start,through,url])),kind=kind,key=key,start=start,through=through,url=url,priority=priority,**extra)

def make_tasks(registry,start,through):
    tasks=[]
    for kind,rows in [('entity',registry['entities']),('topic',registry['topics'])]:
        for row in rows:
            for first,last in windows(start,through):
                key=row.get('key',row.get('id'));url=search_url(row['rssTemplate'],row['query'],first,last)
                base=task(kind,key,first,last,url,row.get('priority','P1'),workstream=row.get('workstream',''),name=row['name'])
                tasks.append(base)
                # Retain English plus relevant local-language editions for selected markets.
                if kind=='entity':
                    for edition in LANGUAGES.targets(row):
                        local_query=LOCAL.QUERY_ALIASES.get(row['id'],row['query']) if edition['language']=='Indonesian' else row['query']
                        native=LANGUAGES.NATIVE_ALIASES.get(row['id'],[])
                        if native:local_query='('+local_query+' OR '+' OR '.join('"'+a+'"' for a in native)+')'
                        ceid_language={'pt-BR':'pt-419','es-419':'es-419','zh-CN':'zh-Hans','zh-TW':'zh-Hant','zh-HK':'zh-Hant'}.get(edition['hl'],edition['hl'].split('-')[0])
                        template='https://news.google.com/rss/search?'+urllib.parse.urlencode(dict(hl=edition['hl'],gl=edition['gl'],ceid=edition['gl']+':'+ceid_language))
                        local_url=search_url(template,local_query,first,last)
                        tasks.append(task(kind,key,first,last,local_url,row.get('priority','P1'),parentId=base['id'],
                            workstream=row.get('workstream',''),name=row['name'],language=edition['language'],market=edition['market'],searchPurpose='Local-language coverage'))
    groups=['(ride-hailing OR "food delivery" OR robotaxi OR "quick commerce" OR "electric motorcycle")',
        '(fintech OR payments OR "digital bank" OR BNPL OR "digital identity")',
        '(funding OR acquisition OR investment OR IPO) (delivery OR mobility OR fintech)',
        '(GoTo OR Gojek OR Grab OR Shopee OR foodpanda OR "Mercado Libre") (earnings OR policy OR partnership OR innovation)']
    for publisher in registry['publishers']:
        for index,group in enumerate(groups):
            query=f'site:{publisher["domain"]} {group}'
            for first,last in windows(start,through):
                url=search_url('https://news.google.com/rss/search?hl=en-US&gl=ID&ceid=ID:en',query,first,last)
                tasks.append(task('publisher',publisher['domain']+':'+str(index),first,last,url,publisher['priority'],name=publisher['name']))
    # Feeds are checked again at run time. A historical XML check is not an uptime guarantee.
    for source in registry['sources']:
        feed=source.get('Feed URL') or ''
        if feed.startswith('https://'):
            tasks.append(task('feed',source['Source ID'],start,through,feed,source['Priority'],name=source['Resource']))
    return tasks

def split_task(parent):
    start=dt.date.fromisoformat(parent['start']);end=dt.date.fromisoformat(parent['through'])
    length=(end-start).days+1
    if length<=1:return []
    step=7 if length>7 else 1;children=[]
    original=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(parent['url']).query)).get('q','')
    while start<=end:
        last=min(end,start+dt.timedelta(days=step-1))
        url=search_url(parent['url'],original,start.isoformat(),last.isoformat())
        child=task(parent['kind'],parent['key'],start.isoformat(),last.isoformat(),url,parent['priority'],parentId=parent['id'],name=parent.get('name',''),workstream=parent.get('workstream',''))
        children.append(child);start=last+dt.timedelta(days=1)
    return children

def parse_feed(body):
    root=ET.fromstring(body)
    tag=root.tag.rsplit('}',1)[-1].lower()
    if tag not in {'rss','feed','rdf'}:raise ValueError('Response is not an RSS/Atom feed')
    # GLOBAL.parse supports RSS and Atom; an unknown RDF format is an access gap, not empty coverage.
    if tag=='rdf':raise ValueError('RDF feed needs a supported parser')
    rows=GLOBAL.parse(body)
    expected=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
    if expected and not rows:raise ValueError('Feed entries exist but none have usable title, URL and date')
    return rows

def fetch(url):
    for attempt in range(2):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'GoToResearch/1.1 public RSS metadata reader','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
            with urllib.request.urlopen(request,timeout=15) as response:
                body=response.read(5_000_001)
                if len(body)>5_000_000:raise ValueError('Feed exceeds 5 MB limit')
                return body
        except urllib.error.HTTPError as error:
            if error.code in (401,403,404,410) or attempt:raise
        except (OSError,TimeoutError):
            if attempt:raise
        time.sleep(.5)

def matches(entity,title):
    identity={'id':entity['id'],'name':entity['name']}
    if entity['key'].startswith('GB:'):
        native=LANGUAGES.NATIVE_ALIASES.get(entity['id'],[])
        if any(alias in title for alias in native):
            if entity['id'] in ('talabat','jahez','tamara','tabby'):return bool(re.search(r'شركة|منصة|تطبيق|توصيل|تقسيط|مدفوعات|تمويل|أرباح|استحواذ|أسهم',title))
            if entity['id']=='ola':return bool(re.search(r'इलेक्ट्रिक|स्कूटर|टैक्सी|कैब|अग्रवाल|मोबिलिटी',title))
            if entity['id']=='porter':return bool(re.search(r'लॉजिस्टिक|डिलीवरी|कार्गो|ट्रक|स्टार्टअप',title))
            if entity['id']=='robinhood':return bool(re.search(r'อาหาร|เดลิเวอรี|ส่งอาหาร|แอป',title))
            return not bool(re.search(GLOBAL.GLOBAL_EXCLUDE,title,re.I))
        return GLOBAL.hit(identity,title)
    return LOCAL.entity_matches(identity,title) and LOCAL.relevant({'entityId':identity['id'],'title':title})

_IDENTITY_CACHE={}

def ingest(rows,job,registry,records):
    retained=0
    bykey={e['key']:e for e in registry['entities']}
    for row in rows:
        if not job['start']<=row['date']<=job['through']:continue
        title=row['title']; suffix=' - '+row.get('sourceName','')
        if row.get('sourceName') and title.endswith(suffix):title=title[:-len(suffix)]
        if job['kind']=='entity' and not matches(bykey[job['key']],title):continue
        identities=_IDENTITY_CACHE.get(title)
        if identities is None:
            identities=[e['key'] for e in registry['entities'] if matches(e,title)]
            if len(_IDENTITY_CACHE)>50000:_IDENTITY_CACHE.clear()
            _IDENTITY_CACHE[title]=identities
        # Topic/feed leads may be relevant to macro or policy without a company mention.
        # Keep them in research only; company attribution still requires an identity match.
        key=digest(canonical(row['url'])+'|'+row['date'])
        old=records.get(key,{})
        records[key]={**row,'id':key,'title':title,'entityKeys':sorted(set(old.get('entityKeys',[])+identities)),
            'taskIds':sorted(set(old.get('taskIds',[])+[job['id']])),
            'topicKeys':sorted(set(old.get('topicKeys',[])+([job['key']] if job['kind']=='topic' else []))),
            'publicationDate':row['date'],'eventDate':None,'reportingPeriod':None,
            'firstDiscoveredAt':old.get('firstDiscoveredAt',stamp()),'lastSeenAt':stamp(),
            'reviewed':False,'verified':False,'reviewStatus':'Needs original-source review',
            'deduplicationNote':'URL/date identity; similar headlines and syndicated event duplicates require editorial reconciliation.'}
        retained+=1
    return retained

def due(job,ledger,now,through):
    saved=ledger.get(job['id'])
    if not saved:return True
    if saved['status']=='split':return False
    age=(now-dt.datetime.fromisoformat(saved['checkedAt'])).total_seconds()
    if saved['status']=='source-unavailable':return age>=3600
    if saved['status']=='capped':return age>=86400
    return age>=(21600 if job['kind']=='feed' or job['through']==through else 604800)

def choose(tasks,ledger,now,through,limit,kind):
    buckets={k:[] for k in ('entity','topic','publisher','feed')}
    for job in tasks:
        if (kind=='all' or kind==job['kind']) and due(job,ledger,now,through):buckets[job['kind']].append(job)
    for bucket in buckets.values():
        bucket.sort(key=lambda j:(j['through']!=through, j['priority'], j['id'] in ledger, -int(j['through'].replace('-','')),j['key']))
    result=[]
    while len(result)<limit and any(buckets.values()):
        for bucket in buckets.values():
            if bucket and len(result)<limit:result.append(bucket.pop(0))
    return result

def choose_balanced(tasks,ledger,now,through,limit,kind):
    """Rotate months and workstreams; one publisher query per domain before its next topic."""
    families={k:{} for k in ('entity','topic','publisher','feed')}
    for job in tasks:
        if (kind=='all' or kind==job['kind']) and due(job,ledger,now,through):
            month=job['start'][:7] if job['kind']!='feed' else 'snapshot'
            families[job['kind']].setdefault(month,[]).append(job)
    rings={}
    for family,months in families.items():
        ring=collections.deque()
        for month,rows in sorted(months.items()):
            groups={}
            for job in sorted(rows,key=lambda j:(j['id'] in ledger,not bool(j.get('searchPurpose')),j['priority'],j.get('parentId') is None,j['key'])):
                group=job['key'].rsplit(':',1)[0] if family=='publisher' else job.get('workstream',family)
                groups.setdefault(group,collections.deque()).append(job)
            # Publisher order follows the curated source priorities in task generation.
            if family=='publisher':
                ranks={t['key'].rsplit(':',1)[0]:i for i,t in reversed(list(enumerate(tasks))) if t['kind']=='publisher'}
                groups=dict(sorted(groups.items(),key=lambda item:ranks.get(item[0],999999)))
            ordered=collections.deque()
            while any(groups.values()):
                for group in groups.values():
                    if group:ordered.append(group.popleft())
            if ordered:ring.append(ordered)
        rings[family]=ring
    result=[]
    while len(result)<limit and any(rings.values()):
        for ring in rings.values():
            if not ring or len(result)>=limit:continue
            queue=ring.popleft();result.append(queue.popleft())
            if queue:ring.append(queue)
    return result

def coverage(registry,tasks,ledger,records):
    baseline={r[0]:r for r in registry['baselineCoverage']}; result=[]
    byparent={}; recordids={}; eligibleids={}
    for t in tasks:
        if t.get('parentId'):byparent.setdefault(t['parentId'],[]).append(t)
    for record in records.values():
        for tid in record['taskIds']:recordids.setdefault(tid,set()).add(record['id'])
        for tid in record.get('eligibleTaskIds',record['taskIds']):eligibleids.setdefault(tid,set()).add(record['id'])
    def descendants(tid):
        children=byparent.get(tid,[])
        return children+[child for t in children for child in descendants(t['id'])]
    for job in tasks:
        if job['kind']!='entity' or job.get('parentId'):continue
        saved=ledger.get(job['id'],{}); children=descendants(job['id'])
        pending=sum(1 for t in children if not byparent.get(t['id']) and (t['id'] not in ledger or ledger[t['id']]['status'] in {'source-unavailable','capped'}))
        discovered=set(recordids.get(job['id'],set()))
        for child in children:discovered.update(recordids.get(child['id'],set()))
        eligible=set(eligibleids.get(job['id'],set()))
        for child in children:eligible.update(eligibleids.get(child['id'],set()))
        month=int(job['start'][5:7]);row=baseline.get(job['key'],[])
        base=row[6+month] if len(row)>6+month and job['start'].startswith(registry['asOf'][:4]) else ''
        result.append(dict(entityKey=job['key'],name=job['name'],month=job['start'][:7],priority=job['priority'],
            discoveryStatus=saved.get('status','not-checked'),lastAttemptAt=saved.get('checkedAt',''),
            reviewedRecordsAtPlanDate=base,baselineAsOf=registry['asOf'],
            discoveredRecords=len(discovered),candidateRecords=len(eligible),quarantinedRecords=len(discovered-eligible),
            unresolvedSplitWindows=pending,editorialStatus='Needs primary review',
            meaning='Search attempts and indexed records only; never proof of exhaustive coverage or no events.'))
    return result

SECTOR_PATTERN=re.compile(r'ride.hail|robotaxi|autonomous.*(?:car|vehicle|taxi)|driverless|food.delivery|grocery|quick.commerce|parcel|courier|logistic|last.mile|electric.*(?:vehicle|motorcycle|taxi|fleet)|battery.swap|fintech|payment|wallet|digital.bank|banking|BNPL|buy.now.pay|lending|loan|credit|merchant|point.of.sale|QRIS|underwriting|digital.identity|KYC|e.commerce|ojek|taksi|pengiriman|pinjaman|kredit|pembiayaan|pendanaan.*(?:fintech|bank|ojek)|pembayaran|dompet|kasir|产业金融|金融|支付|外卖|网约车|融资|物流|銀行|配達|金融|대출|결제|배달|pinjol|tabungan',re.I)
TOPIC_PATTERNS={
 'T01':r'ride.hail|mobility|taxi|taksi|ojek|trips|pangsa pasar',
 'T02':r'food|delivery|restaur|makanan|pesan.antar',
 'T03':r'grocery|groceries|quick.commerce|belanja|sembako',
 'T04':r'parcel|logistic|courier|delivery|kurir|pengiriman',
 'T05':r'merchant|restaur|commission|take.rate|komisi|pedagang',
 'T06':r'driver|rider|ojek|pengemudi|komisi|gig.worker|transport',
 'T07':r'electric|EV fleet|motor listrik|baterai|battery|charging',
 'T08':r'autonomous|robotaxi|driverless|self.driv|otonom|无人驾驶|自动驾驶',
 'T09':r'wallet|QRIS|fintech|dompet|pembayaran|GoPay|ShopeePay|payments|transaksi',
 'T10':r'BNPL|pay.?later|buy.now.pay|kredit|loan|lending|credit',
 'T11':r'loan|lending|credit|pinjaman|penagihan|kredit|pinjol',
 'T12':r'bank|deposit|DPK|NIM|tabungan|simpanan',
 'T13':r'payment|gateway|settlement|QRIS|pembayaran|merchant',
 'T14':r'POS|kasir|merchant|retail.software|point.of.sale',
 'T15':r'SME|UMKM|merchant|lending|microfinanc|modal|pinjaman',
 'T16':r'identity|KYC|biometric|fraud|cyber|signature|identitas|tanda.tangan|penipuan|data.breach',
 'T19':r'IPO|buyback|treasury|listing|repurchase|saham|bursa',
 'T20':r'earnings|revenue|EBITDA|GMV|TPV|results|pendapatan|kinerja|laba',
 'T22':r'bank|payment|lending|OJK|QRIS|POJK|pinjol|pembayaran|kredit',
 'T23':r'tax|pajak|PPh|marketplace|PMK|DJP',
 'T24':r'KPPU|antitrust|competition|persaingan|merger|acquisition|akuisisi',
 'T25':r'halal|BPJPH|food.safety|consumer|perlindungan|makanan',
 'T26':r'MSCI|FTSE|frontier|standalone|market.classification|investability|investabil',
 'T27':r'Fitch|Moody|S&P|JCR|Dagong|CCXI|sovereign|rating|peringkat|outlook',
 'T28':r'beta|WACC|equity.risk|cost.of.capital|Damodaran|country.risk',
 'T29':r'inflation|CPI|consumer.confidence|retail.sales|inflasi|keyakinan.konsumen|eceran|daya.beli',
 'T30':r'household|consumer.credit|consumer.spending|rumah.tangga|kredit.konsum|belanja',
 'T31':r'Bank.Indonesia|BI.?Rate|interest.rate|JISDOR|rupiah|liquidity|likuid|money.supply|M2|suku.bunga|moneter',
 'T32':r'business.activity|capacity.utilization|inventory|industrial|manufactur|produksi|kapasitas|dunia.usaha|persediaan',
 'T33':r'tourism|tourist|vehicle|motorcycle|car.sales|wisata|kendaraan|sepeda.motor|mobil',
 'T34':r'App.Store|Google.Play|review|rating|ulasan',
}

def classify_records(state,registry):
    """Keep raw evidence, quarantine noise and correct stale namesake associations."""
    bykey={e['key']:e for e in registry['entities']};sources={s['Source ID']:s for s in registry['sources']}
    for record in state['records'].values():
        title=record['title'];record['entityKeys']=[key for key in record.get('entityKeys',[]) if key in bykey and matches(bykey[key],title)]
        accepted=[];rejected=[]
        for tid in record['taskIds']:
            job=state['attempts'].get(tid,{})
            if job.get('kind')=='entity':
                good=job.get('key') in record['entityKeys']
            elif job.get('kind')=='topic':
                pattern=TOPIC_PATTERNS.get(job['key'])
                good=bool(re.search(pattern,title,re.I)) if pattern else bool(SECTOR_PATTERN.search(title))
            else:
                good=bool(record['entityKeys'] or SECTOR_PATTERN.search(title) or job.get('key')=='BIS')
            (accepted if good else rejected).append(tid)
            if job.get('kind')=='feed' and not record.get('sourceName'):
                source=sources.get(job['key'],{})
                record['sourceName']=source.get('Resource','Unknown source')
                record['sourceUrl']=source.get('Website / dataset','')
        record['eligibleTaskIds']=accepted;record['rejectedTaskIds']=rejected
        record['relevanceStatus']='Candidate — original-source review required' if accepted else 'Quarantined — identity / subject mismatch'
        record['topicKeys']=sorted({state['attempts'][tid]['key'] for tid in accepted if state['attempts'][tid].get('kind')=='topic'})

def save_outputs(output,state,registry,tasks,through):
    output.mkdir(parents=True,exist_ok=True)
    classify_records(state,registry)
    state['through']=through;state['updatedAt']=stamp()
    state['extraTasks']=[t for t in tasks if t.get('parentId')]
    temporary=output/'state.tmp';temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2));temporary.replace(output/'state.json')
    rows=coverage(registry,tasks,state['attempts'],state['records'])
    with (output/'coverage.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['entityKey']);writer.writeheader();writer.writerows(rows)
    manual=[]
    for s in registry['sources']:
        attempts=[a for a in state['attempts'].values() if a['kind']=='feed' and a['key']==s['Source ID']]
        latest=max(attempts,key=lambda a:a['checkedAt']) if attempts else {}
        manual.append({'kind':'source','key':s['Source ID'],'name':s['Resource'],'url':s['Website / dataset'],
            'status':'Feed discovery plus primary review' if s.get('Feed URL') else 'Needs permitted website / licensed dataset review',
            'lastValidatedAtPlanDate':s['Checked on'],'lastFeedAttemptAt':latest.get('checkedAt'),
            'lastFeedAttemptStatus':latest.get('status','not-checked'),'accessNotes':s['Access and interpretation notes']})
    for m in registry['macro']:
        manual.append({'kind':'macro-history','key':m['id'],'name':m['name'],'url':m['url'],
            'status':'Needs primary time-series reconciliation','latestPeriodAtPlanDate':m['latestPeriod'],
            'target':m['target'],'scopeGuard':m['scopeGuard']})
    (output/'primary-review-queue.json').write_text(json.dumps(manual,ensure_ascii=False,indent=2))
    active_ids={t['id'] for t in tasks}
    active_attempts={k:v for k,v in state['attempts'].items() if k in active_ids}
    summary={'updatedAt':state['updatedAt'],'through':through,'sourceResources':len(registry['sources']),
        'entityRegistryRows':len(registry['entities']),'topicQueries':len(registry['topics']),
        'plannedSearchAndFeedTasks':len(tasks),'attemptedTasks':len(active_attempts),'retainedHistoricalAttempts':len(state['attempts'])-len(active_attempts),
        'notCheckedTasks':sum(t['id'] not in state['attempts'] for t in tasks),
        'blockedTasks':sum(a['status']=='source-unavailable' for a in active_attempts.values()),
        'cappedTasks':sum(a['status']=='capped' for a in active_attempts.values()),
        'unreviewedDiscoveryRecords':len(state['records']),
        'candidateRecords':sum(bool(r['eligibleTaskIds']) for r in state['records'].values()),
        'quarantinedRecords':sum(not r['eligibleTaskIds'] for r in state['records'].values()),
        'searchesRequiringNarrowerWindows':sum(a['status']=='split' for a in active_attempts.values()),
        'publishedAutomatically':0,
        'caveat':'Registry rows overlap. Zero leads, blocked access, unsearched windows and reviewed evidence are different states. No exhaustive completeness claim.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--from',dest='start',default='2026-01-01');ap.add_argument('--through',default=dt.datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat());ap.add_argument('--limit',type=int,default=50);ap.add_argument('--kind',choices=['all','entity','topic','publisher','feed'],default='all');ap.add_argument('--output',type=Path,default=HERE/'results');ap.add_argument('--plan-only',action='store_true');ap.add_argument('--balanced-months',action='store_true');ap.add_argument('--workers',type=int,default=6);ap.add_argument('--baseline-only',action='store_true');ap.add_argument('--current-window-only',action='store_true',help='Refresh current cutoff-window searches and live feeds before older successful windows');ap.add_argument('--unsearched-only',action='store_true');ap.add_argument('--checkpoint-every',type=int,default=50);args=ap.parse_args()
    if not 1<=args.limit<=500:ap.error('--limit must be 1–500')
    if not 1<=args.workers<=8:ap.error('--workers must be 1–8')
    if args.start>args.through:ap.error('--from must not follow --through')
    dt.date.fromisoformat(args.start);dt.date.fromisoformat(args.through)
    if dt.date.fromisoformat(args.through)>dt.datetime.now(ZoneInfo('Asia/Jakarta')).date():ap.error('--through cannot be a future date')
    registry=read(HERE/'registry.json',{});state=read(args.output/'state.json',{'attempts':{},'records':{},'extraTasks':[]})
    tasks=make_tasks(registry,args.start,args.through);ids={t['id'] for t in tasks}
    tasks.extend(t for t in state.get('extraTasks',[]) if t['id'] not in ids and t['start']>=args.start and t['through']<=args.through)
    all_tasks=tasks
    if args.baseline_only:tasks=[t for t in tasks if not t.get('parentId')]
    if args.current_window_only:tasks=[t for t in tasks if t['through']==args.through or t['kind']=='feed']
    eligible_tasks=[t for t in tasks if t['id'] not in state['attempts']] if args.unsearched_only else tasks
    selector=choose_balanced if args.balanced_months else choose
    jobs=[] if args.plan_only else selector(eligible_tasks,state['attempts'],dt.datetime.now(dt.timezone.utc),args.through,args.limit,args.kind)
    def retrieve(url):
        try:return parse_feed(fetch(url)),None
        except Exception as error:return [],str(error)[:300]
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
    # Fetch identical URLs once, while processing and checkpointing state on one thread.
    futures={url:pool.submit(retrieve,url) for url in dict.fromkeys(j['url'] for j in jobs)}
    for i,job in enumerate(jobs,1):
        attempt={'checkedAt':stamp(),'url':job['url'],'start':job['start'],'through':job['through'],'kind':job['kind'],'key':job['key']}
        rows,error=futures[job['url']].result()
        if error:attempt.update(status='source-unavailable',error=error,returned=None,retained=None)
        else:
            count=ingest(rows,job,registry,state['records']);children=[]
            if len(rows)>=100 and job['kind']!='feed':
                edition=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(job['url']).query)).get('hl','en-US')
                # Complete language breadth before unlimited deepening of high-volume feeds.
                # A capped localized result remains an explicit unresolved access limit.
                if edition=='en-US':children=split_task(job)
            status='split' if children else 'capped' if len(rows)>=100 else 'leads-awaiting-review' if count else 'searched-no-leads'
            if job['kind']=='feed' and len(rows)>=100:status='bounded-feed-snapshot'
            attempt.update(status=status,returned=len(rows),retained=count,potentiallyTruncated=len(rows)>=100,
                reviewStatus='Unreviewed',historicalCoverage='Bounded discovery; not exhaustive')
            for child in children:
                if child['id'] not in {t['id'] for t in tasks}:tasks.append(child)
        previous=state['attempts'].get(job['id'],{});attempt['attemptCount']=previous.get('attemptCount',0)+1
        state['attempts'][job['id']]=attempt
        print(f'{i}/{len(jobs)} {job["kind"]} {job["key"]}: {attempt["status"]}',flush=True)
        # Periodic atomic checkpoints bound recovery loss without repeatedly rewriting a growing archive.
        state['extraTasks']=list({t['id']:t for t in all_tasks+tasks if t.get('parentId')}.values())
        if i%max(1,args.checkpoint_every)==0 or i==len(jobs):
            args.output.mkdir(parents=True,exist_ok=True);temp=args.output/'state.tmp';temp.write_text(json.dumps(state,ensure_ascii=False));temp.replace(args.output/'state.json')
    pool.shutdown(wait=True)
    tasks=list({t['id']:t for t in all_tasks+tasks}.values())
    print(json.dumps(save_outputs(args.output,state,registry,tasks,args.through),indent=2))
if __name__=='__main__':main()
