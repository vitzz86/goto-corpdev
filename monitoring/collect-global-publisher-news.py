#!/usr/bin/env python3
"""Collect attributed public RSS headline leads; never treat discovery as reviewed news.

No paywalls or logged-in services are accessed. Google News is used only as a
publisher-indexed RSS discovery layer; source publication dates remain separate
from collection timestamps. Existing public archive leads may be reused after a
fresh exact-identity/context check. RSS query caps and source failures are audited.
"""
import argparse, functools, concurrent.futures, datetime as dt, email.utils, hashlib, html, importlib.util, json, re, time, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PUBLISHERS=[
 ('DealStreetAsia','dealstreetasia.com','https://www.dealstreetasia.com/feed/'),
 ('Tech in Asia','techinasia.com','https://www.techinasia.com/feed'),
 ('Bloomberg','bloomberg.com','https://feeds.bloomberg.com/technology/news.rss'),
 ('Reuters','reuters.com',None),('TechCrunch','techcrunch.com','https://techcrunch.com/feed/'),
 ('Nikkei Asia','asia.nikkei.com',None),('CNBC','cnbc.com','https://www.cnbc.com/id/100727362/device/rss/rss.html'),
 ('e27','e27.co','https://e27.co/feed/'),('Fintech Singapore','fintechnews.sg','https://fintechnews.sg/feed/'),
 ('TechCabal','techcabal.com','https://techcabal.com/feed/'),('Disrupt Africa','disruptafrica.com','https://disruptafrica.com/feed/'),
 ('Rest of World','restofworld.org','https://restofworld.org/feed/'),('Contxto','contxto.com','https://contxto.com/feed/'),
 ('LatamList','latamlist.com','https://latamlist.com/feed/'),('Bloomberg Línea','bloomberglinea.com',None),
 ('The Paypers','thepaypers.com',None),('Finextra','finextra.com','https://www.finextra.com/rss/headlines.aspx'),
 ('Sifted','sifted.eu','https://sifted.eu/feed'),('BusinessWire','businesswire.com',None),
 ('PR Newswire','prnewswire.com','https://www.prnewswire.com/rss/news-releases-list.rss'),
 ('Korea Economic Daily','kedglobal.com',None),('South China Morning Post','scmp.com','https://www.scmp.com/rss/91/feed'),
 ('YourStory','yourstory.com','https://yourstory.com/feed'),('Entrackr','entrackr.com','https://entrackr.com/feed/')]
# Shared research registry drives publisher coverage; unavailable feeds use search fallback.
_registry_path=ROOT/'monitoring/registry.json'
if _registry_path.exists():
 _publisher_registry=json.loads(_registry_path.read_text())['publishers']
 PUBLISHERS=[(s['name'],s['domain'],s.get('feedUrl') if s.get('feedStatus','').startswith('Verified RSS/Atom XML') else None) for s in _publisher_registry]
ALIASES={
 'lulalend':['Lulalend','Lula'],

 '99':['99','99Pay','99Taxi'],'99food':['99Food'], 'bank_jago_gopay_tabungan':['Bank Jago','GoPay Tabungan'],
 'gopay_tabungan_by_jago':['GoPay Tabungan'], 'blue_bird':['Blue Bird','Bluebird'],
 'xanh_sm':['Xanh SM','Green SM','GSM'], 'nu':['Nubank','Nu Holdings'],
 'mercado_libre_mercado_envios':['Mercado Libre','MercadoLibre','Mercado Envios','Mercado Envíos'],
 'ual':['Ualá','Uala'], 'didi_food':['DiDi Food','DidiFood'], 'jd_food_delivery':['JD Food Delivery','JD Takeaway','JD.com food'],
 'line_man':['LINE MAN','LINE MAN Wongnai'], 'go':['GO taxi','GO Inc.','GO Inc','GO株式会社'],
 'up':['Up','Up Bank','Up banking','Up debit'], 'be':['Be Group','beBike','beCar','Be ride-hailing'],
 'advance-ai':['ADVANCE.AI','ADVANCE AI'], 'smile_id':['Smile ID','Smile Identity'],
 'gopay_pinjam':['GoPay Pinjam'], 'gopay_merchant':['GoPay Merchant'],
 'blu':['BCA Digital','blu by BCA'], 'menu':['menu delivery','menu food delivery','menu株式会社'],
 'm_pesa':['M-Pesa','MPesa'], 'wave':['Wave Mobile Money','Wave Senegal','Wave fintech','Wave money'],
 'roam':['Roam','Roam Electric','Roam motorcycle','Roam Kenya','Roam Africa'],
 'wing':['Wing','Wing drone','Wing delivery','Alphabet Wing'], 'wonder':['Wonder','Wonder Group','Wonder food','Wonder restaurant','Wonder delivery'],
 'zip':['Zip Co','Zip Pay','Zip BNPL'], 'stone':['StoneCo','Stone Pagamentos','Stone payments'],
 'square':['Square','Square payments','Square merchant','Square POS','Block Square','Square banking','Square Financial'],
 'persona':['Persona','Persona identity','Persona verification','Persona KYC','Persona biometric'],
 'momo':['MoMo','MoMo Vietnam','MoMo wallet','MoMo fintech','MoMo payments'],
 'maya':['Maya Philippines','Maya wallet','Maya fintech','Maya app','Maya Bank'],
 'ovo':['OVO','OVO Indonesia','OVO wallet','OVO payment','OVO fintech'],
 'toast':['Toast POS','Toast restaurant','Toast payments','Toast Inc','Toast platform'],
 'skip':['SkipTheDishes','Skip the Dishes','Skip delivery','Skip Canada'],
 'foody':['Foody Cyprus','Foody delivery'], 'demae_can':['Demae-can','Demaecan','Demae Can'],
 'swap':['SWAP Energi','Swap Energy'], 'v_green':['V-Green','VGreen'],
 'jenius':['Jenius'], 'seabank':['SeaBank','Sea Bank'], 'paypay':['PayPay'],
 'checkers_sixty60':['Checkers Sixty60','Sixty60'], 'mr_d':['Mr D','Mr Delivery'],
 'swiggy_instamart':['Swiggy Instamart','Instamart'], 'starling_bank':['Starling Bank'],
 'taobao_instant_commerce':['Taobao Instant Commerce','Taobao Shangou','Taobao flash','Taobao instant retail'],
 'uzum_bank':['Uzum Bank'], 'uzum_business':['Uzum Business'], 'uzum_nasiya':['Uzum Nasiya'], 'uzum_tezkor':['Uzum Tezkor'],
 'revolut_bank_uab':['Revolut Bank'], 'unico':['Unico','Unico identity','Unico biometric','Unico IDtech'],
 'dana':['DANA'], 'alva':['ALVA'], 'maxim':['Maxim'], 'astro':['Astro'], 'vida':['VIDA'], 'privy':['Privy'], 'moka':['Moka'],
 'bolt':['Bolt'], 'porter':['Porter'], 'chime':['Chime'], 'gocar':['GoCar'], 'gobox':['GoBox'], 'electrum':['Electrum'],
 'lightspeed':['Lightspeed Commerce','Lightspeed POS','Lightspeed restaurant','Lightspeed retail'],
 'linx':['Linx','Linx retail','Linx POS','Linx payments','Linx Totvs','Linx Stone','Linx software'],
 'stuart':['Stuart','Stuart delivery','Stuart courier','Stuart logistics'], 'flink':['Flink delivery','Flink grocery','Flink groceries'],
 'roadie':['Roadie','Roadie delivery','Roadie UPS','Roadie logistics','Roadie courier'], 'picnic':['Picnic','Picnic grocery','Picnic groceries','Picnic supermarket'],
 'zeller':['Zeller','Zeller payments','Zeller fintech','Zeller business','Zeller terminal'],
 'tabby':['Tabby'], 'tamara':['Tamara'], 'tala':['Tala'], 'fairmoney':['FairMoney'], 'nuro':['Nuro'],
}
CONTEXT={
 'lulalend':r'south.africa|south.african|SME|business.funding|trevor.gosling|working.capital|lulapay',

 'zeller':r'payment|fintech|eftpos|terminal|banking|australia|australian|merchant|point.of.sale|\bPOS\b',
 'stuart':r'delivery|courier|logistic|last.mile|livraison|coursier|entrega|mensajer',
 'roadie':r'\bUPS\b|delivery|logistic|courier|last.mile|shipping|parcel',
 'unico':r'identity|identidade|biometr|IDtech|verifica|autentica',

 'advance-ai':r'advance\.ai|advance intelligence group|advance ai.*(?:kyc|identity|biometric|fintech|fraud)|(?:kyc|biometric|fintech|fraud).*advance ai',
 'ampersand':r'ampersand.*(?:electric|motorcycle|battery|e.mobility)|(?:electric|motorcycle|battery).*ampersand|rwanda|kenya',
 'robinhood':r'thailand|thai|purple ventures|scbx|yip in tsoi|robinhood.*(?:food|delivery|restaurant)',
 'mollie':r'payment|fintech|merchant|checkout|financial|dutch|netherlands',
 'moove':r'fleet|uber|waymo|mobility|driver|vehicle|ride.hail|vehicle.financ',
 'prospa':r'australia|australian|new zealand|ASX|business.lend|small.business.loan',
 'foody':r'cyprus|cypriot|nicosia|limassol|larnaca',
 'xanh_sm':r'xanh.?sm|green.?sm|vinfast|vingroup|electric.*(?:taxi|vehicle|fleet)|taxi|ride.hail|mobility|giao th[ôo]ng',
 '99':r'\bBrazil|Brasil|brasileir|DiDi|ride.hail|taxi|mobility|99pay|99taxi|99food',
 'electrum':r'gojek|goto|\btbs\b|indonesia|motor listrik|electric motorcycle|battery swap|electric scooter',
 'jenius':r'bank|smbc|btpn|rekening|tabungan|nasabah|saldo|kredit|debit|rupiah|deposit|savings|qris|paylater|flexi',
 'maxim':r'ride.hailing|taxi|taksi|transportation|ojek|indonesia|driver|motorcycle',
 'astro':r'grocer|belanja|sembako|astro.*(?:commerce|delivery|quick.commerce)|(?:indonesian|indonesia).*grocer',
 'vida':r'digital identity|identity verification|indonesia|kyc|digital sign',
 'privy':r'indonesia|digital sign|electronic sign|identitas|signature|tanda tangan|harumi|mahendra',
 'moka':r'\bpos\b|kasir|goto|gojek|merchant|restaurant|retail|payment|point.of.sale',
 'dana':r'dompet|fintech|wallet|qris|payment|pembayaran|saldo|financial|transaksi|ant group|espay',
 'alva':r'indonesia|motor listrik|motorcycle|scooter|iman',
 'bolt':r'ride.hail|taxi|scooter|driver|mobility|food delivery|robotaxi|ride.shar|transport|estonia|estonian|tallinn',
 'porter':r'logistics|delivery|truck|cargo|india|funding|unicorn|valuation',
 'chime':r'bank|fintech|financial|ipo|nasdaq|deposit|payment|credit|lending|chime financial',
 'tabby':r'fintech|bnpl|pay.later|payment|financial|funding|ipo|valuation|saudi|uae|dubai',
 'tamara':r'fintech|bnpl|pay.later|payment|financial|funding|saudi|uae|dubai',
 'tala':r'fintech|lending|loan|credit|financial|funding|philippines|kenya|mexico',
 'gocar':r'gojek|indonesia', 'gobox':r'gojek|indonesia|logistics',
 'affirm':r'holdings|AFRM|fintech|bnpl|buy.now.pay|pay.later|payment|lending|loan|credit|max levchin|debit|card|merchant|checkout',
 'momo':r'vietnam|vietnamese|m.service|mservice|nguyen manh|vietnamplus|viet nam|saigon|hanoi',
 'wonder':r'food hall|restaurant|grubhub|marc lore|new york|new jersey|swedesboro|wonder group|wonder delivery|wonder food hall',
 'addi':r'colombia|colombian|fintech|bnpl|buy.now.pay|pay.later|lending|loan|credit|financial|payment|santiago suarez',
 'ola':r'ride.hail|taxi|mobility|electric|scooter|motorcycle|driver|cab|bhavish|aggarwal|ola consumer',
 'tyro':r'payments|merchant|fintech|banking|terminal|australia|acquiring',
 'pargo':r'logistics|parcel|courier|pickup|pick.up|ecommerce|e.commerce|delivery|last.mile',
 'veho':r'parcel|logistics|last.mile|delivery|shipper|shipping|warehous',
 'didi':r'ride.hail|taxi|didi global|didi autonomous|didi food|robotaxi|chauffeur|driver|didi chuxing|mobility|didiglobal|didi.*(?:hong kong|listing|ipo)|didi china',
 'grab':r'ride.hail|taxi|super.app|grabfood|grabpay|grabfin|grabmart|gxs|gxbank|anthon.y? tan|grab holdings|grabbike|mobility|singapore.*grab|grab.*singapore|atome|gopay|gojek|shopee|didi|foodpanda|buyback|grab.*earnings|grab.*revenue|grab.*profit|grab.*acquir|grab.*invest|grab.*\$|grab.*driver|grab.*delivery|grab.*fintech|grab.*robots|grab.*hiring|grab.*vietnam|grab.*indonesia|grab.*malaysia|grab.*thai|grab.*philippines',
 'rapido':r'ride.hail|taxi|bike taxi|cab|rapido.*(?:funding|driver|india|swiggy|zomato|bengaluru|uber|ola)',
 'ovo':r'indonesia|wallet|fintech|grab|nabung|superbank|pembayaran|transaksi|judol|dompet|ovo.*payment|ovo.*qris|ovo.*gopay|ovo.*dana',
 'square':r'payment|merchant|\bpos\b|block|banking|financial services|cash app|restaurant|jack dorsey',
 'persona':r'persona.*(?:identity verification|identity security|identity research|identity platform|identity provider|identity service|kyc|verif|biometric|funding|series [abcd]|raises|rick song|discord|openai)|(?:identity.verification|id.verification|kyc|discord|rick song).*persona',
 'picnic':r'grocery|groceries|supermarket|online grocer',
 'linx':r'brasil|brazil|totvs|stone|retail|\bpos\b|linx.*software',
 'gopay':r'indonesia|indonesian|gojek|goto|qris|rupiah|gopay.*(?:pinjam|tabungan|later|jago|pembayaran|aplikasi|saldo|transaksi)',
 'gofood':r'gojek|goto|indonesia|indonesian|gopay|gofood.*(?:mitra|merchant|resto|omzet|pesan|makanan)',
 'goride':r'gojek|goto|indonesia|indonesian|gopay|ojek',
 'gosend':r'gojek|goto|indonesia|indonesian|gopay',
 'gomart':r'gojek|goto|indonesia|indonesian|gopay|belanja',
 'doku':r'payment|pembayaran|fintech|qris|merchant|gateway|digital wallet|nusa satu inti|jokul|doku.*(?:transaksi|bayar|wallet)',
 'amartha':r'fintech|lending|microfinan|micro.financ|amartha.*(?:funding|loan|pinjaman|keuangan|umkm|financial|invest|pendanaan|pembiayaan|nasabah)',
 'atome':r'bnpl|pay.later|buy.now|payment|checkout|advance intelligence|atome.*(?:financial|card|fintech|shopee|grab|credit|loan|lending|funding)',
 'fantuan':r'delivery|takeaway|takeout|food|restaurant|grocery|fantuan.*(?:funding|round|series|capital)',
 'jahez':r'food|delivery|restaurant|takeaway|jahez group|jahez.*(?:ipo|shares|profit|earnings|revenue|acquisition|acquire)',
 'keeta':r'food|delivery|meituan|restaurant|takeaway',
 'seabank':r'indonesia|indonesian|philippines|philippine|shopee|monee|sea group|qris|ojo|rupiah',
 'segari':r'grocer|sembako|sayur|buah|startup|e.grocery|belanja|segari.*(?:series|funding|raises|delivery)',
 'skip':r'skipthedishes|skip the dishes|food|delivery|takeout|takeaway|restaurant',
 'yassir':r'ride.hail|delivery|algeri|super.app|startup|fintech|yassir.*(?:funding|series|raises|valuation|logistic|taxi)',
 'yoco':r'fintech|payments|merchant|card reader|\bpos\b|yoco.*(?:funding|raises|lending|loan|financial)',
 'redmart':r'grocery|groceries|lazada|singapore|supermarket',
 'menu':r'japan|japanese|tokyo|menu株式会社|kddi|lawson',
 'iseller':r'\bpos\b|indonesia|retail|merchant|point.of.sale|payment|ecommerce',
 'zipline':r'drone|delivery|robot|logistic|funding|aviation|medical supplies',
 'nuro':r'autonomous|vehicle|robot|delivery|self.driv|funding|uber|robotaxi',
 'yape':r'peru|perú|payment|wallet|fintech|bcp|credicorp',
 'yassir':r'ride.hail|algeria|algerian|fintech|delivery|super.app|funding|africa',
 'gozem':r'africa|ride.hail|mobility|fintech|delivery|funding',
 'wing':r'drone|delivery|alphabet',
 'roam':r'kenya|kenyan|roam electric|roam motorcycle|africa.*(?:electric|motorcycle)|roam.*(?:electric motorcycle|motorcycle factory)',
 'up':r'Up Home|Up Bank|Bendigo|Ferocia|Up banking|Up Saver|Up.*(?:Aussies|Australia|neobank)',
 'be':r'vietnam|vietnamese|be.?bike|be.?car|ride.hail|vpbank|be group.*(?:transport|driver|mobility)',
 'go':r'japan|japanese|tokyo|nikkei|waymo|go inc\.',
 'wave':r'africa|african|senegal|senegalese|dakar|ivory coast|côte d.ivoire|mali|burkina|uganda|wave mobile money',
 'blue_bird':r'indonesia|indonesian|jakarta|taxi|taksi|bali|mybluebird|armada|mobilitas|bandara|blue.?bird.*(?:laba|pendapatan|dividen|rupiah)',
}
EXCLUDE={
 'lulalend':r'da silva|president|presidente|brazil|brasil|politic',

 'zeller':r'cody zeller|real estate|zeller realty|basketball|\bNBA\b',
 'roadie':r'concert|guitar|musician|touring crew',

 'blue_bird':r'school bus|bus sekolah|bluebird bio|blue bird corporation',
 'ampersand':r'ampersand capital partners|ampersand growth equity|ampersand group|ampersand education|ampersand ai|ampersand ai|ampersand.*digital advertising',
 'robinhood':r'robinhood markets|vlad tenev|nasdaq.?hood|stock.trading|brokerage|crypto.trading',
 'prospa':r'nigeria|nigerian|lagos',
 'electrum':r'bitcoin|electrumsv|cryptocurr|crypto wallet|blockchain|mining|gold deposit|electrum group|electrum capital|silver exploration',
 'jenius':r'macross|chogokin|valkyrie|maximilian|toy.people|action figure',
 'astro':r'astros|astrophys|astrology|astro malaysia|astro holdings|astro awani|astro television|satellite tv|astro bot|k.pop|moonbin',
 'maxim':r'maxim group|investment bank|ryde ipo|maxim magazine|maxim integrated|maxim healthcare',
 'alva':r'timothy|accident|funeral|obituary|norway|norwegian|alva industries|arcticstartup',
 'bolt':r'bolt.new|stackblitz|usain|lightning bolt|chevrolet bolt|bolt ev|bolt action|bolt biotherapeutics|ryan breslow|bolt financial|bolt checkout',
 'porter':r'porter airlines|porter air|porter robinson|michael porter|michael.*porter jr|kevin porter|denver nuggets',
 'chime':r'chime bell|wind chime|chime music|chime sound|church.*chime|chime communications|amazon chime',
 'dana':r'dana white|dana bash|dana incorporated|dana inc\.|dana farber|dana-farber|dana point|dana air|research funding|dana indonesia raya',
 'tala':r'tala park|tala rugby|tala safwan|tala nad\b',
 'go':r't.money|kleenex|london fashion',
 'be':r'warrant|swedish|sweden|vinay raghav|core.?nergy|high school|las vegas raiders',
 'didi':r'mamata|banerjee|bengal|trinamool|bjp|honorific|sister|didi ko|didi detention',
 'grab':r'grab (?:your|a |an |the |this |these |some |free |their )|cash grab|land grab|power grab|smash.and.grab|grab a bite|grammy|grammys',
 'addi':r'addi industries|addind|addi mason|addi cutshall|addi debord|abiy addi|tigray|athlete of the week',
 'vida':r'virtual care|oura|wearable|oncology|cancer|vida health|vida medical',
 'chime':r'chime in|chime on|chime of|chime over|church bell|amazon chime',
 'rapido':r'model train|rapido trains|rapido bus|motorhome|campervan',
 'ovo':r'ovo energy|drake|ovo sound|ovo arena|october.s very own',
 'gopay':r'czech|czechia|gopay czech|česk|prague',
 'gomart':r'gomart gas|gomart convenience|west virginia|charleston|gomart ballpark',
 'persona':r'mamata|banerjee|electoral|politic|persona [345]|\brpg\b|atlus|metaphor|video game|gaming|game awards|persona series|persona.*(?:creators|characters)',
 'picnic':r'family picnic|annual picnic|church picnic|company held.*picnic|annual family|picnic basket|picnic blanket',
 'wonder':r'wonder woman|wonder man|marvel',
 'doku':r'jeremy doku|jérémy doku|football|soccer|manchester city|man city|winger|premier league',
 'amartha':r'prathidina|soundtrack|movie|film|cinema',
 'atome':r'uranium|mining|potash|atome plc|green fertil|paraguay|atome energy',
 'fantuan':r'fantuan comics|fantuan manga|漫画',
 'jahez':r'kafan|movie|film|soundtrack',
 'keeta':r'vaccaro|tyreek|nfl|football wife',
 'roam':r'roam transit|banff|canadian|canada|roam charging|uk charging|scottish|scotland',
 'seabank':r'vietnam|vietnamese|southeast asia commercial|seabank vietnam',
 'segari':r'turtle|turtles|tiktok|conservation|wildlife|hatchery',
 'skip':r'\bfiba\b|curling|basketball|skip canada',
 'wing':r'wing loong|fixed.wing|x.wing|vampire|skydio|shahed|ukrain|military|russia|heavy bomber',
 'square':r'logan square|time square|times square|square riddim|steppers version|town square|city square',
 'yassir':r'zouaoui|mckinsey|moroccan football',
 'yoco':r'froyo|celebrity',
 'alva':r'timothy|accident|funeral|obituary|norway|norwegian|alva industries|arcticstartup',
 'persona':r'mamata|banerjee|electoral|politic|persona [345]|\brpg\b|atlus|metaphor|video game|gaming|game awards|persona series|persona.*(?:creators|characters)',
 'affirm':r'christian|terminally ill|dignity|sermon|bishop',
 'afterpay':r'afterpay arena|tame impala|noah kahan|concert|live review.*gallery',
 'wing':r'wing loong|fixed.wing|x.wing|vampire|skydio|shahed|ukrain|military|russia|heavy bomber',
 'porter':r'porter road|porter family|harry porter|porter airlines|porter robinson|michael porter|kevin porter',
 'square':r'logan square|time square|times square|square riddim|steppers version|town square|city square',
 'privy':r'ethereum|web3|crypto wallet|privy.io|privy wallet|cryptocurrency|stablecoin wallet|stripe.*privy|privy.*stripe',
 '99':r'\b99[%％]|highway 99|route 99|real madrid|football legend|fc 26|\€1[.,]99|accuracy|sexing',
}
GLOBAL_EXCLUDE=r'saldo dana gratis|dana kaget|game penghasil|aplikasi penghasil uang|slot gacor|\btogel\b|live withdraw|bokep|porn|xxx|onlyfans|university athletics|match highlights|macross|chogokin|valkyrie'

@functools.lru_cache(maxsize=4096)
def compiled(pattern,flags=re.I):
 return re.compile(pattern,flags)
def search(pattern,text,flags=0):
 return compiled(pattern,flags).search(text)
def norm(s):
 return re.sub(r'[^\w]+',' ',html.unescape(s).casefold()).strip()
def aliased(p):
 return ALIASES.get(p['id'],[p['name']])
def hit(p,title):
 lower=title.casefold()
 if not any(a.casefold() in lower for a in aliased(p)):return False
 if search(GLOBAL_EXCLUDE,title,re.I): return False
 if search(r'stock price, news, quote.*history|investors heavily search|shares.*gf score|awaiting anthropic.*aoc interview|customer service: how to|app download: how to|stock rated.*moderate buy|wall street analysts believe|\bform [34]\b|marketbeat|downdetector status|broker (?:raises|cuts|maintains).*target|maintains.*(?:buy|sell|hold) rating|keeps.*target.*stock',title,re.I):return False
 if search(r'should you buy|buy or sell\??|price prediction|stock forecast|is .* stock (?:a buy|undervalued)|should (?:value )?investors buy|earnings expected to grow|stock: buy or sell|promo code|coupon code',title,re.I):return False
 if not any(search(r'(?<!\w)'+re.escape(a)+r'(?!\w)',title,re.I) for a in aliased(p)):return False
 if p['id'] in EXCLUDE and search(EXCLUDE[p['id']],title,re.I):return False
 if p['id']=='dana' and not search(r'(?<!\w)DANA(?!\w)',title):return False
 if p['id']=='99' and not search(r'99Pay|99Taxi|DiDi.?99|DiDi/99|(?:app|platform|company|aplicativo|plataforma) 99\b|\b99(?:,| [a-z]+)?[^.]{0,100}(?:DiDi|ride.hail|mobility|taxi|driver|motorista)|(?:DiDi|ride.hail|mobility|taxi|driver|motorista)[^.]{0,100}\b99\b',title,re.I):return False
 return p['id'] not in CONTEXT or bool(search(CONTEXT[p['id']],title,re.I))
def query(p):
 aliases=aliased(p)
 q=' OR '.join('"'+a.replace('"','')+'"' for a in aliases)
 q='('+q+')' if len(aliases)>1 else q
 # These names are ambiguous even before downstream filtering.
 qualifier={
  'xanh_sm':'(taxi OR "Green SM" OR "Xanh SM" OR VinFast OR mobility)',
  'square':'(payments OR merchant OR POS OR Block OR banking)', 'persona':'(identity OR KYC OR biometric OR verification)', 'linx':'(Brazil OR retail OR software OR TOTVS OR Stone)', 'picnic':'(grocery OR groceries OR supermarket)', 'wonder':'(restaurant OR Grubhub OR \"Marc Lore\" OR \"food hall\")', 'momo':'(Vietnam OR Vietnamese)', 'roam':'(electric OR motorcycle OR Kenya)', 'wing':'(drone OR delivery OR Alphabet)',
  '99':'(Brazil OR Brasil OR DiDi OR 99Pay OR taxi)', 'electrum':'(Gojek OR TBS OR Indonesia OR "electric motorcycle")',
  'jenius':'(bank OR SMBC OR BTPN OR rekening)', 'maxim':'(taxi OR "ride hailing" OR ojek)',
  'astro':'(groceries OR grocery OR Indonesia)', 'vida':'("digital identity" OR biometric OR Indonesia)',
  'privy':'(Indonesia OR signature OR "digital identity")', 'moka':'(POS OR kasir OR merchant OR Gojek)',
  'dana':'(wallet OR fintech OR QRIS OR pembayaran OR Espay)', 'alva':'(Indonesia OR motorcycle OR scooter)',
  'bolt':'(mobility OR taxi OR "ride hailing" OR delivery OR funding)',
  'chime':'(bank OR fintech OR financial OR IPO)', 'porter':'(logistics OR India OR delivery)',
  'tabby':'(fintech OR BNPL OR payments OR Saudi)', 'tamara':'(fintech OR BNPL OR Saudi)',
  'tala':'(fintech OR lending OR loan OR credit)', 'zipline':'(drone OR delivery OR funding)',
  'nuro':'(autonomous OR delivery OR vehicle OR robotaxi)',
 }.get(p['id'],'')
 return q+' '+qualifier if qualifier else q

def get(url):
 last=None
 for attempt in range(3):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'GoToResearch/1.0 public RSS reader (+https://vitzz86.github.io/goto-corpdev/)','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9'})
   with urllib.request.urlopen(req,timeout=25) as r:
    b=r.read(5_000_001)
    if len(b)>5_000_000:raise ValueError('Feed exceeds 5 MB safety bound')
    if not b:raise ValueError('Empty response')
    return b, str(r.status)
  except urllib.error.HTTPError as e:
   last=f'HTTP {e.code}'
   if e.code in (401,403,404,410):break
  except Exception as e:last=str(e)
  time.sleep(.6*(attempt+1))
 raise RuntimeError(last)

def parse(b):
 root=ET.fromstring(b);out=[]
 items=root.findall('.//item')
 if not items:items=root.findall('.//{http://www.w3.org/2005/Atom}entry')
 for item in items:
  def t(k):
   e=item.find(k)
   return ''.join(e.itertext()).strip() if e is not None else ''
  title=html.unescape(t('title') or t('{http://www.w3.org/2005/Atom}title'))
  url=t('link')
  if not url:
   e=item.find('{http://www.w3.org/2005/Atom}link');url=e.get('href','') if e is not None else ''
  pub=t('pubDate') or t('{http://www.w3.org/2005/Atom}published') or t('{http://www.w3.org/2005/Atom}updated')
  try:date=email.utils.parsedate_to_datetime(pub).date().isoformat()
  except Exception:
   try:date=dt.datetime.fromisoformat(pub.replace('Z','+00:00')).date().isoformat()
   except Exception:continue
  source=item.find('source'); name=''.join(source.itertext()).strip() if source is not None else ''
  source_url=source.get('url','') if source is not None else ''
  byline=t('{http://purl.org/dc/elements/1.1/}creator') or t('author')
  if title and url.startswith(('https://','http://')):out.append({'title':title,'url':url,'date':date,'sourceName':name,'sourceUrl':source_url,'byline':byline})
 return out

def canonical(u):
 s=urllib.parse.urlsplit(u);qs=urllib.parse.parse_qsl(s.query)
 return urllib.parse.urlunsplit((s.scheme,s.netloc.lower(),s.path.rstrip('/'),urllib.parse.urlencode([(k,v) for k,v in qs if not k.startswith('utm_') and k not in ('oc','ref','source','fbclid','gclid')]),''))
def domain(u):return urllib.parse.urlsplit(u).netloc.lower().removeprefix('www.')
def newsurl(q,start,end,lang='en-US',country='US'):
 return 'https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':f'{q} after:{start} before:{end}','hl':lang,'gl':country,'ceid':country+':'+lang.split('-')[0]})

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=6);ap.add_argument('--skip-archive',action='store_true');ap.add_argument('--limit',type=int,default=0);ap.add_argument('--split-cap',type=int,default=270);ap.add_argument('--offline',action='store_true');ap.add_argument('--through',default='2026-10-16');ap.add_argument('--self-test',action='store_true');ap.add_argument('--per-company-month',type=int,default=10);args=ap.parse_args()
 universe=json.loads((ROOT/'research/global-universe.json').read_text());players=universe['players'];byid={p['id']:p for p in players}
 if args.self_test:
  tests=[('99food','Highway 99 food cart hub',False),('99food','CADE investigates 99Food in Brazil',True),('99','Brazil football legend lost 99% of earnings',False),('99','99Pay raises $135M via FIDC',True),('up','Turkey steps up banking ties',False),('be','BE Group elevates Vinay Raghav',False),('be','Be Group battery swapping in Vietnam',True),('go','Kleenex Glow and Go Taxi London Fashion Week',False),('go','Japan taxi app GO Inc. launches Tokyo IPO',True),('bolt','Ryan Breslow raises funding to save Bolt',False),('bolt','Bolt ride-hailing expands in Italy',True),('dana','Aturan Dana Fintech Lending',False),('dana','DANA wallet fintech investment Indonesia',True),('momo','MoMo Payments Ghana GRA',False),('momo','MoMo Vietnam wallet launch',True),('wing','Skydio Fixed-Wing Drone',False),('wing','Walmart expands Wing drone delivery',True),('porter','Porter Road meat delivery review',False),('porter','Porter logistics truck India',True),('electrum','Electrum Group mining bitcoin',False),('electrum','TBS GOTO Electrum motor listrik EBITDA',True),('affirm','Christians Affirm Dignity',False),('affirm','Affirm merchant payment launch',True)]
  tests += [('didi','Your Didi is with you Mamata condemns Dipke detention',False),('didi','DiDi Global expands autonomous ride-hailing operations',True),('grab','Grab your new smartphone today',False),('grab','Grab Holdings reports revenue growth in Singapore',True),('ola','Ola Aurell sets rebellion to music',False),('ola','Ola ride-hailing expands electric cab fleet',True),('addi','Athlete of the Week Addi Cutshall',False),('addi','Addi Colombia BNPL fintech raises new funding',True),('tyro','Star Wars Tyro Squadron Adventures',False),('tyro','Tyro Payments launches new merchant terminal',True),('roam','Why super tuskers Roam Africa',False),('roam','Roam Electric expands motorcycle fleet in Kenya',True),('privy','Privy stablecoin wallet engine for Stripe AWS fintech',False),('privy','Privy Indonesia digital signature platform partnership',True),('vida','Vida Oura wearable data virtual care',False),('vida','VIDA Indonesia digital identity biometric service',True),('pargo','Jeremy Pargo vs Warriors stats',False),('pargo','Pargo parcel pickup logistics expansion',True),('swap','Gaming mouse hot-swap battery review',False),('swap','SWAP Energi battery network Indonesia',True),('blue_bird','Bluebird Group partnership Bertram Capital',False),('blue_bird','Blue Bird Indonesia taxi fleet expansion',True),('gopay','GoPay Czech payment gateway expands',False),('gopay','GoPay Indonesia wallet introduces QRIS payment service',True)]
  tests += [('persona',"Protest To Persona: How Mamata Banerjee's Stand Against SIR Is Now An Electoral Identity",False),('persona','Persona expands identity verification for fintech customers',True),('doku','Jeremy Doku Manchester City winger football scores',False),('doku','DOKU payment gateway expands merchant services',True),('alva','Timothy Alva motorcycle accident',False),('alva','ALVA Indonesia electric scooter launch',True),('amartha','Amartha Prathidina movie soundtrack',False),('amartha','Amartha fintech lending funding Indonesia',True),('atome','Atome PLC Paraguay green fertiliser mining',False),('atome','Atome BNPL payment card partnership',True),('fantuan','Fantuan Comics Meituan manga',False),('jahez','Jahez Ya Kafan movie soundtrack',False),('keeta','Keeta Vaccaro NFL football wife',False),('keeta','Meituan Keeta food delivery expands Saudi Arabia',True),('roam','Roam Transit Canadian electric buses Banff',False),('seabank','Vietnam SeABank banking expansion',False),('seabank','SeaBank Philippines banking partnership Shopee',True),('segari','Segari turtle conservation hatchery',False),('skip','FIBA Canada skip basketball championship',False),('square','Logan Square restaurant neighborhood market',False),('wing','China Wing Loong drone deliveries',False),('yassir','Yassir Zouaoui McKinsey leadership',False),('yoco','Yoco Froyo celebrity',False)]
  for pid,title,want in tests:assert hit(byid[pid],title)==want,(pid,title,want)
  print(f'{len(tests)} positive/negative entity regression cases passed');return
 start='2026-01-01';through=args.through;before=(dt.date.fromisoformat(through)+dt.timedelta(days=1)).isoformat();stamp=dt.datetime.now(dt.timezone.utc).isoformat();rawdir=ROOT/'research/raw/global-publisher-news';rawdir.mkdir(parents=True,exist_ok=True)
 tasks=[]
 for p in players[:args.limit or None]:
  q=query(p);tasks.append({'kind':'company','playerId':p['id'],'query':q,'url':newsurl(q,start,before),'from':start,'through':through})
 # Target publisher domains in smaller topic groups to prevent a single broad query monopolising results.
 groups=['(ride-hailing OR "food delivery" OR robotaxi OR "quick commerce" OR "electric motorcycle")','(fintech OR payments OR "digital bank" OR BNPL OR "digital identity")','(Grab OR GoTo OR Gojek OR GoPay OR foodpanda OR "99Food" OR Nubank OR "Mercado Pago")','(funding OR acquisition OR investment OR IPO) (delivery OR mobility OR fintech)']
 for name,dom,feed in PUBLISHERS:
  if feed:tasks.append({'kind':'publisher-feed','publisher':name,'publisherDomain':dom,'url':feed,'from':start,'through':through})
  for group in groups:
   q=f'site:{dom} {group}';tasks.append({'kind':'publisher-search','publisher':name,'publisherDomain':dom,'query':q,'url':newsurl(q,start,before),'from':start,'through':through})
 # Native-language indexed discoveries supplement English for important markets.
 for pid,lang,country in [('99food','pt-BR','BR'),('99','pt-BR','BR'),('ifood','pt-BR','BR'),('mercado_pago','es-419','MX'),('rappi','es-419','CO'),('dana','id','ID'),('jenius','id','ID')]:
  p=byid[pid];q=query(p);tasks.append({'kind':'company-language','playerId':pid,'query':q,'url':newsurl(q,start,before,lang,country),'from':start,'through':through})
 results=[];audit=[]
 previous_path=ROOT/'research/global-publisher-news.json'
 previous_audit={a['url']:a for a in json.loads(previous_path.read_text()).get('queryAudit',[])} if previous_path.exists() else {}
 def run(task):
  cache=rawdir/(hashlib.sha256(task['url'].encode()).hexdigest()[:20]+'.xml')
  try:
   if cache.exists() and cache.stat().st_size:b=cache.read_bytes();status='Cached public feed'
   elif args.offline:
    old=previous_audit.get(task['url'],{})
    raise RuntimeError(old.get('error','No cached public feed; offline audit'))
   else:b,http=get(task['url']);cache.write_bytes(b);status='Fetched HTTP '+http
   rows=parse(b);return task,rows,{'status':status,'feedItems':len(rows),'possibleTruncation':len(rows)>=100}
  except Exception as e:return task,[],{'status':'Source unavailable','error':str(e),'feedItems':0,'possibleTruncation':False}
 def harvest(task,rows,info):
  kept=0
  for r in rows:
   if not start<=r['date']<=through:continue
   # A query hit or publisher name alone is insufficient identity evidence.
   identity_title=r['title']
   identity_source=r.get('sourceName') or task.get('publisher','')
   if identity_source and identity_title.endswith(' - '+identity_source):identity_title=identity_title[:-len(' - '+identity_source)]
   pids=[p['id'] for p in players if hit(p,identity_title)]
   if not pids:continue
   if not r['sourceName']:r['sourceName']=task.get('publisher','Publisher')
   if not r['sourceUrl']:r['sourceUrl']='https://'+task.get('publisherDomain',domain(r['url']))
   # Preserve direct publisher feed URLs and attributed indexed publisher labels.
   title=r['title'];suffix=' - '+r['sourceName']
   if title.endswith(suffix):title=title[:-len(suffix)]
   if task.get('publisherDomain')=='dealstreetasia.com' and search(r'bloomberg|reuters',r.get('byline',''),re.I):continue
   results.append({**r,'title':title,'playerIds':pids,'publisherDomain':task.get('publisherDomain') or domain(r['sourceUrl']),'feedUrl':task['url'],'collectionMethod':task['kind']});kept+=1
  audit.append({**task,**info,'matchedBeforeDedup':kept,'checkedAt':stamp})
 with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(args.workers,10))) as pool:
  for idx,(task,rows,info) in enumerate(pool.map(run,tasks)):
   harvest(task,rows,info)
   if idx%25==0:print(f'Fetched {idx+1}/{len(tasks)} queries; matched {len(results)} headline links',flush=True)
 # Split the most capped company feeds into calendar-month windows, with a bound to keep reruns manageable.
 capped=[a for a in audit if a['kind']=='company' and a.get('possibleTruncation')][:args.split_cap]
 split=[]
 for task in capped:
  for month in range(1,int(through[5:7])+1):
   s=f'2026-{month:02d}-01';e=f'2026-{month+1:02d}-01' if month<int(through[5:7]) else before
   split.append({**{k:task[k] for k in ('playerId','query')},'kind':'company-month','url':newsurl(task['query'],s,e),'from':s,'through':(dt.date.fromisoformat(e)-dt.timedelta(days=1)).isoformat()})
 if split:
  with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(args.workers,10))) as pool:
   for idx,(task,rows,info) in enumerate(pool.map(run,split)):
    harvest(task,rows,info)
    if idx%50==0:print(f'Monthly refinement {idx+1}/{len(split)}; matched {len(results)} headline links',flush=True)
 if not args.skip_archive:
  archive=ROOT/'research/2026-news-archive.json'
  if archive.exists():
   for row in json.loads(archive.read_text()).get('records',[]):
    if not start<=row.get('date','')<=through:continue
    title=row['title'];source=row.get('source','Public publisher');suffix=' - '+source
    identity_title=title[:-len(suffix)] if title.endswith(suffix) else title
    pids=[p['id'] for p in players if hit(p,identity_title)]
    if not pids:continue
    if title.endswith(suffix):title=title[:-len(suffix)]
    sourceurl=row.get('sourceUrl','')
    if not sourceurl:
     match=next((d for n,d,f in PUBLISHERS if norm(n)==norm(source) or norm(n) in norm(source)),None)
     if match:sourceurl='https://'+match
    results.append({'title':title,'url':row['url'],'date':row['date'],'sourceName':source,'sourceUrl':sourceurl,'playerIds':pids,'publisherDomain':domain(sourceurl),'feedUrl':row.get('feedUrl',''),'collectionMethod':'Existing monthly archive; identity rechecked'})
 # URL plus normalised-title keys merge Google mirrors and direct publisher feed links.
 unique={};titlekeys={};urlkeys={}
 for r in results:
  ukey=canonical(r['url']);tkey=norm(r['title']);key=urlkeys.get(ukey) or titlekeys.get(tkey)
  if key is None:
   key=hashlib.sha256((tkey+'|'+r['date']).encode()).hexdigest()[:18];unique[key]={**r,'id':'global-news-'+key,'alternateSources':[]};titlekeys[tkey]=key;urlkeys[ukey]=key
  else:
   saved=unique[key];saved['playerIds']=sorted(set(saved['playerIds']+r['playerIds']))
   alt={k:r.get(k,'') for k in ('sourceName','sourceUrl','url','publisherDomain','feedUrl')}
   if alt['url']!=saved['url'] and alt not in saved['alternateSources']:saved['alternateSources'].append(alt)
   if domain(saved['url'])=='news.google.com' and domain(r['url'])!='news.google.com':
    saved['alternateSources'].append({k:saved.get(k,'') for k in ('sourceName','sourceUrl','url','publisherDomain','feedUrl')})
    for k in ('url','sourceUrl','publisherDomain','sourceName'):saved[k]=r.get(k,'')
 records=[]
 for r in unique.values():
  r.update({'summary':'Public publisher/RSS headline; full article not reviewed.','reviewed':False,'evidence':'Publisher headline metadata','type':'News discovery','retrievedAt':stamp})
  records.append(r)
 records.sort(key=lambda r:(r['date'],r['title']),reverse=True)
 full_count=len(records)
 full_path=rawdir/'all-validated-headlines.json'
 full_path.write_text(json.dumps({'asOf':through,'records':records},ensure_ascii=False,separators=(',',':')))
 priority_domains={p[1] for p in PUBLISHERS}
 ranked=sorted(records,key=lambda r:(r.get('publisherDomain') in priority_domains,r['date']),reverse=True)
 slots={};selected=[]
 for r in ranked:
  eligible=[pid for pid in r['playerIds'] if slots.get((pid,r['date'][:7]),0)<args.per_company_month]
  if not eligible:continue
  for pid in r['playerIds']:slots[(pid,r['date'][:7])]=slots.get((pid,r['date'][:7]),0)+1
  r['playerIds']=eligible
  r.pop('feedUrl',None);r.pop('retrievedAt',None);r.pop('summary',None);r.pop('evidence',None)
  for alt in r.get('alternateSources',[]):alt.pop('feedUrl',None)
  selected.append(r)
 records=sorted(selected,key=lambda r:(r['date'],r['title']),reverse=True)
 coverage=[]
 for p in players:
  qa=[a for a in audit if a.get('playerId')==p['id']];rows=[r for r in records if p['id'] in r['playerIds']]
  good=[a for a in qa if not a.get('error')]
  coverage.append({'playerId':p['id'],'status':'Public RSS queried' if good else 'Source queries unavailable' if qa else 'Not queried','queries':len(qa),'successfulQueries':len(good),'retained':len(rows),'latestPublication':max((r['date'] for r in rows),default=None),'sourceErrors':[{'url':a['url'],'error':a['error']} for a in qa if a.get('error')],'possiblyCappedQueries':sum(a.get('possibleTruncation',False) for a in qa),'coverageMeaning':'Selected unique headline leads after exact-identity/context checks and the per-company-month display cap; neither complete news history nor independently reviewed events.'})
 publishers=[]
 for name,dom,feed in PUBLISHERS:
  aa=[a for a in audit if a.get('publisherDomain')==dom]; rr=[r for r in records if r.get('publisherDomain')==dom or any(x.get('publisherDomain')==dom for x in r['alternateSources'])]
  publishers.append({'name':name,'domain':dom,'website':'https://'+dom,'rssUrl':feed,'directFeedStatus':next((a['status'] for a in aa if a['kind']=='publisher-feed'),'No public feed configured'),'queryCount':len(aa),'retained':len(rr),'errors':[{'url':a['url'],'error':a['error']} for a in aa if a.get('error')]})
 out={'asOf':through,'from':start,'through':through,'retrievedAt':stamp,'records':records,'coverage':coverage,'publishers':publishers,'queryAudit':audit,'stats':{'players':len(players),'playersQueried':sum(c['queries']>0 for c in coverage),'playersWithLeads':sum(c['retained']>0 for c in coverage),'records':len(records),'identityFilteredHeadlinesBeforeDisplayCap':full_count,'validatedHeadlinesBeforeDisplayCap':full_count,'displayCapPerCompanyMonth':args.per_company_month,'entityLinks':sum(len(r['playerIds']) for r in records),'queries':len(audit),'queryErrors':sum(bool(a.get('error')) for a in audit),'possibleCappedQueries':sum(a.get('possibleTruncation',False) for a in audit),'publisherDomainsTargeted':len(PUBLISHERS),'directPublicFeedsAttempted':sum(bool(p[2]) for p in PUBLISHERS)},'limitations':[f'Public discovery display is capped at {args.per_company_month} headline rows per company/month, preferring targeted publishers then recency; the full validated research collection is retained separately.','This is public headline discovery, not full-article review or comprehensive licensed-media coverage.','Google News RSS may cap results and omit older stories; bounded monthly refinements reduce but cannot remove this gap.','Publication dates/source dates remain publication metadata, not the date of a research check.','Paywalls and unavailable feeds are recorded; no access restrictions are bypassed.','Missing headlines do not establish that a company has no news, funding, or operational changes.','Similar company names require identity and sector context. All leads require human/source review before an investment decision.','DealStreetAsia public RSS usage is limited to attributed headlines/backlinks; no licensed wire article text is republished.']}
 path=ROOT/'research/global-publisher-news.json';path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
 print(json.dumps({'file':str(path),'stats':out['stats'],'bytes':path.stat().st_size},indent=2),flush=True)

if __name__=='__main__':main()
