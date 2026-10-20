"""Filter exact company ambiguity and spam before publishing RSS leads."""
import re

# Search aliases identify products without requiring an invented exact phrase.
QUERY_ALIASES = {
 "dhs": 'DHS (logistik OR ekspedisi OR kurir) -homeland -immigration -ICE',
 "spx": '("SPX Express" OR "SPX Shopee")',
 "tiki": 'TIKI (kurir OR ekspedisi OR "Titipan Kilat")',
 "mex": '("MEX Berlian" OR "MEX Express" OR "MEX Cargo")',
 "bes": '("Blibli Express" OR "BES Blibli")',

 "jenius": 'Jenius (SMBC OR BTPN OR bank OR Flexi OR rekening)',
 "gocar": 'GoCar (Gojek OR Indonesia)', "gobox": 'GoBox (Gojek OR Indonesia)',
 "moka": 'Moka (POS OR kasir OR GoTo OR Gojek)',
 "selly": 'Selly (GoTo OR Gojek OR merchant OR Indonesia)',
 "electrum": 'Electrum (Gojek OR GoTo OR TBS OR "motor listrik" OR "electric motorcycle")',
 "astro": 'Astro (groceries OR grocery OR Indonesia OR belanja)',
 "maxim": 'Maxim (taxi OR "ride hailing" OR ojek OR Indonesia)',
 "goto": 'GoTo (Gojek OR GoPay OR Tokopedia OR Indonesia)',
 "sea": '"Sea Limited"', "bank_jago": '"Bank Jago"',
 "blue_bird": '(Bluebird OR "Blue Bird") (Indonesia OR taxi OR taksi)',
 "argor": '"Argor Capital"', "argor-funds": '"Argor Capital"',
 "bintang_kecil": '"Bintang Kecil" (GoTo OR Gojek OR investasi OR investment)',
 "monee": 'Monee (Sea OR Shopee OR fintech OR credit)',
 "dana": 'DANA (Indonesia OR wallet OR QRIS OR Espay)',
 "alva": 'ALVA (Indonesia OR motorcycle OR "motor listrik")',
 "vida": 'VIDA (Indonesia OR "digital identity" OR biometric)',
 "privy": 'Privy (Indonesia OR signature OR "tanda tangan")',
 "swap": '"SWAP Energi"', "paper-id": '"Paper.id"',
 "skuad": 'Skuad (Payoneer OR workforce OR payroll)',
 "gojek_sg": 'Gojek Singapore', "amity": '"Amity Solutions"',
 "meeting-ai": '("Meeting.ai" OR MeetingAI) (Indonesia OR transcription)',
 "stash": 'Stash (investing OR fintech OR brokerage OR Grab)',
 "modeli": 'Modeli (AI OR "artificial intelligence")',
 "belli": 'Belli (logistics OR cargo OR freight)',
 "vara": 'Vara (workforce OR Bukugaji OR payroll)',
 "blitz": 'Blitz (logistics OR delivery) Indonesia',
 "somin-ai": '"SOMIN AI"', "mfab": '"Multifinance Anak Bangsa"',
 "seindonesia": 'SeIndonesia', "pickup-coffee": '"Pickup Coffee"',
 "higood": 'HiGOOD Vietnam', "fairatmos": 'Fairatmos',
 "food-market-hub": '"Food Market Hub"', "safeboda": 'SafeBoda',
 "dash-workforce": 'Dash (workforce OR staffing OR employment)',
}
IDENTITY_ALIASES = {"blue_bird": ["bluebird", "blue bird"], "bank_jago": ["bank jago"],
 "jenius": ["jenius"], "gocar": ["gocar"], "astro": ["astro"], "maxim": ["maxim"],
 "moka": ["moka"], "skuad": ["skuad", "payoneer workforce management"],
 "gojek_sg": ["gojek"], "electrum": ["electrum"]}

def search_query(entity, start, before):
    name = entity["name"].split("(")[0].split("/")[0].strip()
    term = QUERY_ALIASES.get(entity["id"], '"' + name.replace('"', '') + '"')
    return term + " after:" + start.isoformat() + " before:" + before.isoformat()

def entity_matches(entity, title):
    name = entity["name"].split("(")[0].split("/")[0].strip()
    aliases = IDENTITY_ALIASES.get(entity["id"], [name])
    return any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", title, re.I) for alias in aliases)

def discovery_kind(title, entity_id):
    # A bank publishing a market note is not a corporate action by that bank.
    if entity_id == "jenius" and re.search(r"market update|market commentary|market outlook|market review|daily market|weekly market|sentimen pasar|ulasan pasar", title, re.I):
        return "Market commentary"
    return "News discovery"

CONTEXT={
 'ovo':r'indonesia|wallet|fintech|grab|nabung|superbank|pembayaran|transaksi|judol|dompet|qris|gopay|dana',
 'wahana':r'logisti|kurir|courier|ekspedisi|pengiriman|paket|express|prestasi|parcel',
 'dhs':r'dhs.*(?:logisti|courier|kurir|ekspedisi)|(?:logisti|courier|kurir|ekspedisi).*dhs',
 'spx':r'shopee|spx express|spx.*(?:logistics|logistik|kurir|ekspedisi|parcel)',
 'tiki':r'tiki.*(?:kurir|ekspedisi|pengiriman|logisti|parcel)|(?:kurir|ekspedisi|pengiriman|logisti|parcel).*tiki|titipan kilat',
 'mex':r'mex.*(?:berlian|logisti|cargo|kargo|ekspedisi)|(?:berlian|logisti|cargo|kargo|ekspedisi).*mex',
 'bes':r'blibli express|blibli.*bes|bes.*blibli',
 'blue_bird':r'indonesia|indonesian|jakarta|taksi|taxi|bali|mybluebird|armada|mobilitas|bandara|blue.?bird.*(?:laba|pendapatan|dividen|rupiah)',
 'grab':r'grab holdings|anthon.y? tan|grabfood|grabpay|grabfin|grabmart|grabbike|grab.*(?:singapore|indonesia|malaysia|thai|vietnam|philippines|earnings|revenue|profit|atome|gojek|driver|delivery|fintech|robotaxi)|(?:singapore|atome|gojek).*grab',

 'argor':r'capital|ventures',
 'dash-workforce':r'workforce|staffing|singapore|employment',
 'blitz':r'logistics|delivery|indonesia',
 'belli':r'logistics|cargo|freight',
 'modeli':r'artificial intelligence|ai platform|ai startup',
 'vara':r'workforce|bukugaji|payroll|employee',
 'electrum':r'gojek|goto|\btbs\b|indonesia|motor listrik|electric motorcycle|battery swap|electric scooter',
 'gocar':r'gojek|indonesia',
 'moka':r'\bpos\b|kasir|goto|gojek|merchant|restaurant|retail|payment|point.of.sale',
 'maxim':r'ride.hailing|taxi|taksi|transportation|ojek|indonesia',
 'selly':r'goto|gojek|merchant|ecommerce|indonesia',
 'goto':r'indonesia|gojek|gopay|tokopedia|rupiah|\bidr\b|idx|thohir|treasury shares|walujo|patuwo',
 'monee':r'sea|shopee|fintech|loan|credit|lending',
 'jenius':r'bank|banking|b[tp]pn|smbc|fintech|financial|keuangan|tabungan|nasabah|rekening|saldo|kredit|debit|rupiah|deposit|savings|qris|paylater|flexi|spend|investment|digital',
 'gomart':r'gojek|goto|indonesia|belanja|grocery|layanan|mitra',
 'multipolar':r'indonesia|lippo|mlpl|investment company|investment holding|multipolar (?:tbk|technology)',
 'advance-ai':r'advance[ .-]ai.*(?:identity|verification|kyc|fraud|fintech|singapore|indonesia|group)|advanc[e]? intelligence group',
 'gobox':r'gojek|indonesia|logistics|moving service',
 'alva':r'indonesia|electric|motorcycle|scooter|iman',
 'amity':r'amity solutions|amity.*(?:ai|chatbot|enterprise|thailand)|thai.*amity',
 'meeting-ai':r'meeting\.ai|meetingai|indonesia.*transcrip|bahasa.*transcrip',
 'stash':r'stash.*(?:invest|fintech|financial platform|retirement|brokerage)|(?:invest|fintech).*stash',
 'pluang':r'pluang.*(?:pro mode|launch|partner|funding|capital|users|platform|license)|(?:launch|partner|funding|capital|users|platform|license).*pluang',
 'kitabisa':r'kitabisa|kitabisa\.com',
 'paper-id':r'paper\.id|paperid.*(?:payment|invoice|indonesia)',
 'doku':r'payment|fintech|qris|indonesia|merchant|gateway|e.wallet|digital wallet|pembayaran|transaksi|nusa satu inti',
 'astro':r'grocer|indonesia|belanja|sembako|grocery|commerce|delivery',
 'privy':r'indonesia|digital sign|electronic sign|identitas|signature|tanda tangan|fintech',
 'vida':r'digital identity|identity verification|sign|biometric|indonesia|kyc',
 'dana':r'dompet|fintech|wallet|qris|payment|pembayaran|saldo|financial|transaksi|ant (?:group|international)|espay',
}
def relevant(record):
 title=record.get('title','');publisher=record.get('source','');body=title.rsplit(' - '+publisher,1)[0] if publisher else title
 if re.search(r'bokep|porn|xxx|onlyfans|leaked.*video|viral.*(?:sex|adult)|university athletics|match highlights|brewery|amity brew',body,re.I):return False
 entity=record.get('entityId');pattern=CONTEXT.get(entity)
 if entity=='ovo' and re.search(r'ovo energy|drake|ovo sound|ovo arena|october.s very own',body,re.I):return False
 if entity=='wahana' and re.search(r'dopamine.?land|amusement|taman bermain|wahana wisata',body,re.I):return False
 if entity=='garena' and re.search(r'redeem.?code|kode redeem|free fire.*(?:reward|hadiah|kode)',body,re.I):return False
 if entity=='dhs' and re.search(r'homeland|immigration|deport|\bICE\b|detention|ilhan omar',body,re.I):return False
 if entity=='spx' and re.search(r'spx technologies|s.p.500|shopinx|spx6900',body,re.I):return False
 if entity=='blue_bird' and re.search(r'school bus|bus sekolah|bluebird bio|blue bird corporation',body,re.I):return False
 if entity=='grab' and re.search(r'grab (?:your|a |an |the |this |these |some |free |their )|cash grab|land grab|power grab|smash.and.grab',body,re.I):return False
 if entity=='electrum' and re.search(r'bitcoin|electrumsv|cryptocurr|crypto wallet|blockchain|mining|gold deposit|electrum group|electrum capital|silver exploration',body,re.I):return False
 if entity=='astro' and re.search(r'astros|astrophys|astrology|astro malaysia|astro holdings|astro awani|astro television|satellite tv|astro bot|k.pop|moonbin',body,re.I):return False
 if entity=='dana' and not re.search(r'(?<!\w)DANA(?!\w)',body):return False
 if re.search(r'saldo dana gratis|dana kaget|game penghasil|aplikasi penghasil uang|slot gacor|\btogel\b|live withdraw',body,re.I):return False
 if entity=='dana' and re.search(r'research funding|dana indonesia raya',body,re.I):return False
 if entity=='shopee' and re.search(r'cup.*\d\s*[-:]\s*\d|group [ab]:|match highlights',body,re.I):return False
 if entity=='jenius' and re.search(r'macross|chogokin|valkyrie|maximilian|toy.people|action figure',body,re.I):return False
 if entity=='alva' and re.search(r'norway|norwegian|alva industries|lightweight electric motors|arcticstartup',body,re.I):return False
 if entity=='maxim' and re.search(r'maxim group|investment bank|ryde ipo|maxim magazine|maxim integrated|maxim healthcare',body,re.I):return False
 return not pattern or bool(re.search(pattern,body,re.I))


def clean_records(records):
    """Reconcile merged identity links and remove only unsupported entity matches."""
    cleaned = []
    for record in records:
        entity_ids = list(dict.fromkeys([record.get('entityId')] + record.get('entities', [])))
        retained = [entity_id for entity_id in entity_ids if entity_id and relevant({**record, 'entityId': entity_id})]
        if not retained:
            continue
        row = dict(record)
        if row.get('entityId') not in retained:
            row['entityId'] = retained[0]
            # Avoid displaying the old, rejected entity name after reassignment.
            row['entity'] = retained[0]
        if 'entities' in row:
            row['entities'] = retained
        if not row.get('verified'):
            row['implication'] = 'Unreviewed discovery lead: event-specific relevance and any GoTo implication have not yet been established.'
            row['category'] = discovery_kind(row.get('title', ''), row.get('entityId'))
        cleaned.append(row)
    return cleaned


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Offline quality reconciliation; default is a dry run.')
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    for path in args.files:
        payload = json.loads(path.read_text())
        before = len(payload.get('records', []))
        payload['records'] = clean_records(payload.get('records', []))
        for coverage in payload.get('coverage', []):
            entity_id = coverage.get('entityId', coverage.get('id'))
            if coverage.get('month'):
                coverage['retained'] = sum(entity_id in r.get('entities', [r.get('entityId')]) and r.get('date', '').startswith(coverage['month']) for r in payload['records'])
            elif coverage.get('url'):
                coverage['records'] = sum(r.get('entityId') == entity_id and r.get('feedUrl') == coverage['url'] for r in payload['records'])
            coverage['coverageMeaning'] = 'Retained means source-linked discovery leads after identity filtering, not verified events. Zero leads does not establish no company updates.'
        if args.write:
            path.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
        print(json.dumps({'file': str(path), 'before': before, 'after': len(payload['records']), 'removed': before - len(payload['records']), 'written': args.write}))
