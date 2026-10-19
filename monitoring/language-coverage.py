"""Public-news editions for selected operating markets; not a linguistic footprint claim."""
EDITIONS={
 'Indonesia':('id','ID','Indonesian'),'Brazil':('pt-BR','BR','Portuguese'),
 'India':('hi','IN','Hindi'),'China':('zh-CN','CN','Chinese (simplified)'),
 'Hong Kong':('zh-HK','HK','Chinese (traditional)'),'Taiwan':('zh-TW','TW','Chinese (traditional)'),
 'Japan':('ja','JP','Japanese'),'South Korea':('ko','KR','Korean'),
 'Vietnam':('vi','VN','Vietnamese'),'Thailand':('th','TH','Thai'),
 'Malaysia':('ms','MY','Malay'),'Philippines':('fil','PH','Filipino'),
 'Bangladesh':('bn','BD','Bengali'),'Pakistan':('ur','PK','Urdu'),
 'Nepal':('ne','NP','Nepali'),'Cambodia':('km','KH','Khmer'),
 'Myanmar':('my','MM','Burmese'),'Laos':('lo','LA','Lao'),
 'Mexico':('es-419','MX','Spanish'),'Argentina':('es-419','AR','Spanish'),
 'Colombia':('es-419','CO','Spanish'),'Chile':('es-419','CL','Spanish'),
 'Peru':('es-419','PE','Spanish'),'Spain':('es','ES','Spanish'),
 'France':('fr','FR','French'),'Canada':('fr','CA','French'),
 'Germany':('de','DE','German'),'Austria':('de','AT','German'),
 'Netherlands':('nl','NL','Dutch'),'Italy':('it','IT','Italian'),
 'Portugal':('pt-PT','PT','Portuguese'),'Greece':('el','GR','Greek'),
 'Cyprus':('el','CY','Greek'),'Poland':('pl','PL','Polish'),
 'Sweden':('sv','SE','Swedish'),'Norway':('no','NO','Norwegian'),
 'Denmark':('da','DK','Danish'),'Finland':('fi','FI','Finnish'),
 'Czechia':('cs','CZ','Czech'),'Romania':('ro','RO','Romanian'),
 'Bulgaria':('bg','BG','Bulgarian'),'Croatia':('hr','HR','Croatian'),
 'Serbia':('sr','RS','Serbian'),'Montenegro':('sr','ME','Serbian'),
 'Hungary':('hu','HU','Hungarian'),'Estonia':('et','EE','Estonian'),
 'Lithuania':('lt','LT','Lithuanian'),'Türkiye':('tr','TR','Turkish'),
 'Ukraine':('uk','UA','Ukrainian'),'Georgia':('ka','GE','Georgian'),
 'Armenia':('hy','AM','Armenian'),'Moldova':('ro','MD','Romanian'),
 'Kazakhstan':('ru','KZ','Russian'),'Kyrgyzstan':('ru','KG','Russian'),
 'Uzbekistan':('uz','UZ','Uzbek'),'Saudi Arabia':('ar','SA','Arabic'),
 'United Arab Emirates':('ar','AE','Arabic'),'Egypt':('ar','EG','Arabic'),
 'Iraq':('ar','IQ','Arabic'),'Jordan':('ar','JO','Arabic'),
 'Qatar':('ar','QA','Arabic'),'Kuwait':('ar','KW','Arabic'),
 'Bahrain':('ar','BH','Arabic'),'Oman':('ar','OM','Arabic'),
 'Morocco':('fr','MA','French'),'Algeria':('ar','DZ','Arabic'),
 'Tunisia':('fr','TN','French'),'Senegal':('fr','SN','French'),
 'Côte d’Ivoire':('fr','CI','French'),'Cameroon':('fr','CM','French'),
 'Benin':('fr','BJ','French'),'Togo':('fr','TG','French'),
 'Burkina Faso':('fr','BF','French'),'Mali':('fr','ML','French'),
 'Gabon':('fr','GA','French'),'Republic of the Congo':('fr','CG','French'),
 'Kenya':('sw','KE','Swahili'),'Rwanda':('fr','RW','French'),
}
SPANISH_MARKETS=['Bolivia','Costa Rica','Dominican Republic','Ecuador','El Salvador','Guatemala','Honduras','Nicaragua','Panama','Paraguay','Uruguay','Venezuela']
for country in SPANISH_MARKETS:EDITIONS[country]=('es-419','MX','Spanish')
ENGLISH_MARKETS={'United States','United Kingdom','Australia','New Zealand','Singapore','South Africa','Nigeria','Ghana','Uganda','Zambia'}

NATIVE_ALIASES={
 'phonepe':['फोनपे'],'paytm':['पेटीएम'],'razorpay':['रेजरपे','रेज़रपे'],
 'swiggy':['स्विगी'],'blinkit':['ब्लिंकिट'],'zomato':['ज़ोमैटो','जोमैटो'],
 'zepto':['ज़ेप्टो','जेप्टो'],'rapido':['रैपिडो'],'ola':['ओला'],
 'porter':['पोर्टर'],'pine_labs':['पाइन लैब्स'],
 'talabat':['طلبات'],'jahez':['جاهز'],'tamara':['تمارا'],'tabby':['تابي'],
 'hungerstation':['هنقرستيشن'],'careem':['شركة كريم','تطبيق كريم','كريم باي'],
 'noon':['شركة نون','منصة نون','نون فود'],
 'foodpanda':['ফুডপান্ডা','فوڈپانڈا','ฟู้ดแพนด้า'],
 'go':['GO株式会社','GOアプリ'],
 'didi':['滴滴'],'didi_food':['滴滴外卖'],'meituan':['美团'],
 'alipay':['支付宝'],'wechat_pay':['微信支付'],'taobao_instant_commerce':['淘宝闪购'],
 'jd_instant_retail':['京东秒送'],'baemin':['배달의민족','배민'],
 'coupang_eats':['쿠팡이츠'],'yogiyo':['요기요'],'kakao_mobility':['카카오모빌리티'],
 'kakao_pay':['카카오페이'],'demae_can':['出前館'],'paypay':['ペイペイ'],
 'kaspi_kz':['Каспи'],'yandex_go':['Яндекс Go'],
 'robinhood':['โรบินฮู้ด'],
}

def targets(entity):
    countries=[s.strip() for s in entity.get('markets','').split(';') if s.strip()]
    result=[];seen=set()
    for country in countries:
        if country in ENGLISH_MARKETS:continue
        edition=EDITIONS.get(country)
        if not edition:continue
        hl,gl,label=edition
        # One edition per distinct language, retaining which market supplied it.
        if label in seen:continue
        seen.add(label);result.append(dict(hl=hl,gl=gl,language=label,market=country))
    return result
