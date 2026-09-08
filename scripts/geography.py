"""Country identifiers join official source names to map features without changing raw data."""
EAST_ASIA=['China','Japan','Korea, South','Korea, North','Mongolia','Taiwan','Hong Kong','Macau']
SOUTHEAST_ASIA=['Burma','Thailand','Vietnam','Laos','Cambodia','Malaysia','Indonesia','Philippines','Singapore','Brunei','Timor-Leste']
ALIASES={'Myanmar':'Burma','South Korea':'Korea, South','Republic of Korea':'Korea, South',
    'North Korea':'Korea, North',"Democratic People\'s Republic of Korea":'Korea, North',
    'Viet Nam':'Vietnam','Lao PDR':'Laos',"Lao People\'s Democratic Republic":'Laos',
    'United States of America':'United States','USA':'United States','Russian Federation':'Russia',
    'East Timor':'Timor-Leste','World':'Global'}
MAP_NAMES={'Burma':'Myanmar','Korea, South':'South Korea','Korea, North':'North Korea','United States':'United States of America','Timor-Leste':'East Timor'}
LABELS={'Japan':'日本','Korea, South':'韩国','Korea, North':'朝鲜','Mongolia':'蒙古',
    'Taiwan':'中国台湾','Hong Kong':'中国香港','Macau':'中国澳门','Burma':'缅甸','Laos':'老挝',
    'Cambodia':'柬埔寨','Malaysia':'马来西亚','Singapore':'新加坡','Brunei':'文莱','Timor-Leste':'东帝汶'}

def canonical_country(country):return ALIASES.get(country,country)

def geography_metadata(country):
    country=canonical_country(country)
    return dict(country=country,map_name=MAP_NAMES.get(country,country),label=LABELS.get(country),
        subregion='East Asia' if country in EAST_ASIA else 'Southeast Asia' if country in SOUTHEAST_ASIA else None)
