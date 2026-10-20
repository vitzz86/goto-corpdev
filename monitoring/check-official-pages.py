#!/usr/bin/env python3
"""Audit registry website leads; retrieval never becomes verified news."""
import concurrent.futures,datetime as dt,hashlib,json,urllib.request,urllib.parse
from html.parser import HTMLParser
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
class Text(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.parts=[];self.title=[];self.in_title=False
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg'):self.skip+=1
        if tag=='title':self.in_title=True
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg'):self.skip=max(0,self.skip-1)
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title.append(data.strip())
        if not self.skip and data.strip():self.parts.append(data.strip())
def fetch(url):
    result={'requestedUrl':url,'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'publicationDate':None,'reviewed':False}
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'GoToResearch/1.1 public-source coverage audit'})
        with urllib.request.urlopen(request,timeout=15) as response:
            body=response.read(2000001);result.update(finalUrl=response.url,httpStatus=response.status,contentType=response.headers.get('Content-Type',''))
        if len(body)>2000000:raise ValueError('Response exceeds 2MB audit limit')
        if 'html' not in result['contentType']:raise ValueError('Non-HTML resource; separate document review needed')
        parser=Text();parser.feed(body.decode('utf-8',errors='replace'))
        title=' '.join(parser.title);text='\n'.join(parser.parts)
        blocked=any(term in (title+' '+text[:500]).lower() for term in ['just a moment','access denied','verify you are human','request blocked','attention required!'])
        result.update(status='access-limited' if blocked else 'retrieved-awaiting-review' if len(text)>200 else 'insufficient-readable-content',title=title,text=text[:35000],sha256=hashlib.sha256(body).hexdigest())
    except Exception as error:result.update(status='unavailable',error=str(error)[:300])
    return result
def main():
    registry=json.loads((HERE/'registry.json').read_text());output=ROOT/'research/official-page-checks-20261019-private.json'
    previous=json.loads(output.read_text()).get('pages',{}) if output.exists() else {}
    urls=sorted({e.get('website') for e in registry['entities'] if isinstance(e.get('website'),str) and e['website'].startswith('https://')})
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(fetch,url):url for url in urls if url not in previous}
        for i,future in enumerate(concurrent.futures.as_completed(futures),1):
            url=futures[future];previous[url]=future.result();print(i,len(futures),url,previous[url]['status'],flush=True)
            if i%25==0:output.write_text(json.dumps({'pages':previous},ensure_ascii=False))
    rows=[]
    for e in registry['entities']:
        page=previous.get(e.get('website'),{})
        rows.append({'key':e['key'],'website':e.get('website'),'status':page.get('status','identity-unresolved'),'checkedAt':page.get('checkedAt'),'title':page.get('title'),'publicationDate':None,'reviewed':False,'meaning':'Website retrieval audit only; not verified company news or a dated event.'})
    output.write_text(json.dumps({'pages':previous,'registryRows':rows},ensure_ascii=False))
    public={'asOf':'2026-10-19','registryRows':len(rows),'websiteLeads':len(urls),'checks':rows,'meaning':'Known website leads checked directly. Readable pages still require entity and content review. Missing URLs remain unresolved identities, not no-news conclusions.'}
    (ROOT/'research/official-source-audit-20261019.json').write_text(json.dumps(public,ensure_ascii=False,separators=(',',':')))
    print('Saved official website audit for',len(rows),'registry entries.',flush=True)
if __name__=='__main__':main()
