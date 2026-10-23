"""Additional discovery routes. Configuration never implies source access or verified news."""
import urllib.parse
LANGUAGE_QUERIES={
 'Indonesian':('id','ID','id','(ojol OR taksi OR logistik OR kurir OR pengiriman OR "pesan antar" OR "motor listrik")','(pembayaran OR pinjaman OR pembiayaan OR pendanaan OR akuisisi OR "bank digital" OR QRIS)'),
 'Portuguese':('pt-BR','BR','pt-419','(entregas OR mobilidade OR "transporte por aplicativo" OR "última milha" OR logística)','(pagamentos OR crédito OR fintech OR financiamento OR aporte OR aquisição OR "banco digital")'),
 'Spanish':('es-419','MX','es-419','(reparto OR entregas OR movilidad OR "comercio rápido" OR logística)','(pagos OR crédito OR fintech OR financiación OR inversión OR adquisición OR "banca digital")'),
 'French':('fr','FR','fr','(livraison OR mobilité OR "commerce rapide" OR logistique)','(paiement OR crédit OR fintech OR financement OR acquisition OR "banque numérique")'),
 'German':('de','DE','de','(Lieferdienst OR Mobilität OR Lebensmittellieferung OR Logistik)','(Zahlung OR Kredit OR Fintech OR Finanzierung OR Übernahme OR Digitalbank)'),
 'Chinese':('zh-CN','CN','zh-Hans','(外卖 OR 即时零售 OR 网约车 OR 自动驾驶 OR 物流)','(支付 OR 金融科技 OR 数字银行 OR 融资 OR 收购 OR 信贷)'),
 'Japanese':('ja','JP','ja','(宅配 OR 配達 OR タクシー OR 自動運転 OR 物流)','(決済 OR フィンテック OR デジタル銀行 OR 資金調達 OR 買収 OR 融資)'),
 'Korean':('ko','KR','ko','(배달 OR 모빌리티 OR 택시 OR 자율주행 OR 물류)','(결제 OR 핀테크 OR 인터넷은행 OR 투자유치 OR 인수 OR 대출)'),
 'Vietnamese':('vi','VN','vi','("giao hàng" OR "gọi xe" OR "xe điện" OR "thương mại điện tử")','("thanh toán" OR fintech OR "ngân hàng số" OR "gọi vốn" OR "tín dụng")'),
 'Thai':('th','TH','th','(เดลิเวอรี OR ส่งอาหาร OR เรียกรถ OR โลจิสติกส์)','(ฟินเทค OR ชำระเงิน OR สินเชื่อ OR ระดมทุน OR ธนาคาร)'),
 'Arabic':('ar','SA','ar','(توصيل OR تنقل OR لوجستيات OR تاكسي)','(مدفوعات OR تمويل OR استثمار OR استحواذ OR تقسيط OR بنك)'),
}
MULTILINGUAL_SECTOR=r'entregas|mobilidade|logística|logistica|pagamentos|financiamento|aporte|aquisição|reparto|movilidad|pagos|crédito|financiación|inversión|adquisición|livraison|mobilité|logistique|paiement|financement|banque|Lieferdienst|Mobilität|Zahlung|Finanzierung|Übernahme|Digitalbank|即时零售|网约车|数字银行|收购|信贷|宅配|配達|タクシー|自動運転|物流|決済|資金調達|買収|融資|모빌리티|택시|자율주행|물류|핀테크|인터넷은행|투자유치|인수|giao hàng|gọi xe|xe điện|thanh toán|ngân hàng số|gọi vốn|tín dụng|เดลิเวอรี|ส่งอาหาร|เรียกรถ|ฟินเทค|ชำระเงิน|สินเชื่อ|ระดมทุน|توصيل|تنقل|لوجستيات|مدفوعات|تمويل|استثمار|استحواذ|تقسيط'

def localized_publisher_queries(publisher):
 result=[]
 for language,(hl,gl,ceid,operations,capital) in LANGUAGE_QUERIES.items():
  if language not in publisher.get('language',''):continue
  country=publisher.get('searchCountry') or gl
  # News editions are provider-specific; use known valid editions and keep publisher region separate.
  template='https://news.google.com/rss/search?'+urllib.parse.urlencode(dict(hl=hl,gl=gl,ceid=gl+':'+ceid))
  for group,q in [('operations',operations),('capital-payments',capital)]:
   result.append(dict(key=publisher['domain']+':local:'+language+':'+group,query='site:'+publisher['domain']+' '+q,template=template,language=language,publisherRegion=publisher.get('region',''),editionCountry=gl))
 return result

def official_host(entity):
 raw=entity.get('website') or ''
 host=(urllib.parse.urlsplit(raw).hostname or '').removeprefix('www.')
 if not host or host in {'google.com','facebook.com','instagram.com','linkedin.com','news.google.com'}:return None
 return host
