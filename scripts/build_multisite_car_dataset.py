"""Normalize captured public advertisements without inventing verified sale labels."""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.scrape_multisite_cars import HOSTS, OUTPUT, ROOT

MODEL_BRANDS = {
    'Hyundai': ['Grand i10 Nios', 'Grand i10', 'i20 Active', 'Santro Xing', 'Santro', 'i10', 'i20', 'Creta', 'Venue', 'Verna', 'Tucson', 'Santa Fe', 'Eon', 'Xcent', 'Getz', 'Kona', 'Accent', 'Elantra', 'Ioniq'],
    'Maruti Suzuki': ['Swift Dzire', 'Dzire', 'Swift', 'Alto K10', 'Alto', 'Wagon R', 'Brezza', 'Celerio', 'Baleno', 'Ignis', 'S Cross', 'Ertiga', 'S Presso', 'SX4', 'Zen', 'Omni', 'A Star', 'Fronx', 'Jimny', '800', 'Ritz'],
    'Toyota': ['Land Cruiser Prado', 'Land Cruiser', 'Fortuner', 'Corolla', 'Hilux', 'RAV4', 'Rush', 'Yaris', 'Etios', 'Innova'],
    'Ford': ['EcoSport', 'Freestyle', 'Figo', 'Fiesta', 'Endeavour', 'Ranger'],
    'Kia': ['Seltos', 'Sonet', 'Sportage', 'Picanto', 'Rio', 'Sorento', 'Carens', 'Soul', 'Niro'],
    'Tata': ['Nexon EV', 'Nexon', 'Tiago EV', 'Tiago', 'Safari Storme', 'Safari', 'Indica', 'Indigo', 'Tigor', 'Punch', 'Hexa', 'Sumo', 'Harrier', 'Altroz'],
    'Honda': ['WRV', 'CRV', 'BRV', 'City', 'Brio', 'Amaze', 'Jazz', 'Civic', 'Mobilio'],
    'Renault': ['Kwid', 'Duster', 'Triber', 'Kiger', 'Captur'],
    'Volkswagen': ['CrossPolo', 'Polo', 'Vento', 'Tiguan', 'Taigun', 'Ameo', 'Beetle', 'Touareg'],
    'Skoda': ['Rapid', 'Fabia', 'Octavia', 'Kushaq', 'Yeti', 'Superb'],
    'Nissan': ['Magnite', 'Kicks', 'Sunny', 'Terrano', 'X Trail', 'March', 'Micra', 'Patrol', 'Navara'],
    'Mahindra': ['Scorpio', 'XUV500', 'XUV300', 'KUV100', 'Bolero', 'Thar', 'TUV300', 'Quanto', 'Xylo', 'e2o'],
    'BYD': ['Atto 3', 'Dolphin', 'Sealion 7', 'E6', 'M6'],
    'MG': ['ZS EV', 'ZS', 'Hector', 'Comet'],
    'Daihatsu': ['Terios', 'Sirion', 'Charade', 'Rocky'],
    'Datsun': ['Redi Go', 'Go'],
    'Mitsubishi': ['Outlander', 'Pajero', 'ASX', 'Lancer', 'L200', 'Eclipse Cross'],
    'Chevrolet': ['Spark', 'Beat', 'Aveo', 'Captiva', 'Cruze'],
    'Jeep': ['Compass', 'Wrangler'], 'Skywell': ['ET5'], 'Deepal': ['S07', 'SO7', 'L07'],
    'BMW': [], 'Mercedes-Benz': [], 'Audi': [], 'Suzuki': [], 'Land Rover': [], 'Ssangyong': ['Rexton', 'Tivoli'],
    'Subaru': ['XV'], 'DFSK': ['Glory 580'], 'Kaiyi': ['X3 Pro EV'], 'Dongfeng': ['Nammi Box'],
    'Isuzu': ['V Cross'], 'Leapmotor': ['C10'], 'Peugeot': ['3008'], 'Seres': ['3'],
}


def text(tag):
    return tag.get_text(' ', strip=True) if tag else ''


def redact(value):
    value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[contact omitted]', value or '')
    return re.sub(r'(?<!\d)(?:\+?977[- ]*)?9[678]\d(?:[ -]*\d){7}(?!\d)', '[contact omitted]', value)


def numeric(value):
    match = re.fullmatch(r'\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(?:km|cc|persons|seats)?\s*', str(value or ''), re.I)
    return float(match[1].replace(',', '')) if match else None


def price(value):
    value = re.sub(r'^(?:NRs|NPR|Rs\.?|रू\.)\s*', '', str(value or ''), flags=re.I).strip()
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?', value):
        return None
    return float(value.replace(',', ''))


def match_identity(title, given_brand=None, given_model=None):
    compact = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    for pattern, replacement in [(r'grand\s*nios', 'Grand i10 Nios'), (r'grand\s*i10', 'Grand i10'),
        (r'vanue', 'Venue'), (r'dezire', 'Dzire'), (r'creata', 'Creta'), (r'breeza', 'Brezza'),
        (r'campass', 'Compass'), (r'eco-sport', 'EcoSport'), (r'\b([BCW])R-V\b', r'\1RV'),
        (r'\bET-5\b', 'ET5'), (r'\bmobilo\b', 'Mobilio')]:
        title = re.sub(pattern, replacement, title, flags=re.I)
    brand = given_brand
    if brand:
        brand = next((candidate for candidate in MODEL_BRANDS if candidate.lower() == brand.lower()), brand)
    if brand in ('Suzuki', 'Maruti', 'Maruti suzuki'):
        brand = 'Maruti Suzuki'
    if brand == 'Tata Electric':
        brand = 'Tata'
    if not brand:
        candidates = [(found.start(), -len(candidate), candidate) for candidate in MODEL_BRANDS
                      if (found := re.search(r'\b' + re.escape(candidate) + r'\b', title, re.I))]
        if candidates:
            brand = min(candidates)[2]
            brand = 'Maruti Suzuki' if brand == 'Suzuki' else brand
    matches = []
    for maker, models in MODEL_BRANDS.items():
        if brand and maker != brand:
            continue
        for model in models:
            pattern = r'(?<![A-Za-z0-9])' + r'[\s-]*'.join(re.escape(word) for word in model.split()) + r'(?![A-Za-z])'
            found = re.search(pattern, title, re.I)
            if found:
                matches.append((len(compact(model)), maker, model, found))
    if matches:
        _, maker, model, found = max(matches, key=lambda item: item[0])
        tail = title[found.end():]
        tail = re.split(r'\b(?:19|20)\d{2}\b|\b(?:in|model|only|excellent|immaculate|for|near|like|single|diesel|petrol|full|condition)\b|[|:•–—(]|\[contact', tail, maxsplit=1, flags=re.I)[0]
        variant = tail.strip(' -.,') or None
        return brand or maker, given_model or model, variant
    return brand, given_model, None


def empty_row(host, url, evidence, discovery):
    row = {field: None for field in ('listing_id', 'title', 'brand', 'model', 'variant', 'model_year',
        'asking_price_npr', 'actual_sale_price_npr', 'price_raw', 'odometer_km', 'engine_cc', 'fuel_type',
        'transmission', 'drivetrain', 'condition_claim', 'body_type', 'color', 'location', 'ownership_raw',
        'listing_date', 'listing_date_raw', 'sold_date', 'updated_at_source', 'battery_capacity_kwh', 'range_km',
        'fuel_economy_kmpl', 'manufacturing_country_claim', 'possible_duplicate_group')}
    row.update(record_id=hashlib.sha256(url.encode()).hexdigest()[:20], source_site=host, source_url=url,
        market_country='Nepal', currency='NPR', currency_basis='Nepal marketplace context; no currency conversion',
        vehicle_type='Car', vehicle_condition='used', listing_status='unknown', price_basis='advertised_asking',
        used_inventory_basis='used-car marketplace/dealer context; individual classification not independently verified',
        captured_at_utc=evidence['captured_at_utc'], evidence=[evidence], discovered_from=discovery,
        raw_fields={}, quality_flags=[], image_urls=[], description_excerpt=None,
        independently_verified=False, training_eligible=False, review_status='pending_human_review', reviewer=None)
    return row


def transmission(value):
    if re.search(r'\bmanual\b', value or '', re.I):
        return 'Manual'
    if re.search(r'\b(?:automatic|auto|amt|cvt|ivt|at|dct)\b', value or '', re.I):
        return 'Automatic'
    return None


def drivetrain(value):
    match = re.search(r'\b(?:4\s*[xX]\s*4|[24]\s*WD|AWD|FWD|RWD)\b', value or '', re.I)
    return re.sub(r'\s+', '', match[0]).upper().replace('4X4', '4WD') if match else None


def condition(value):
    match = re.search(r'\b(?:excellent|good|fresh|fair|poor|immaculate|pristine)(?:\s+overall)?\s+condition\b|\bwell[- ]maintained\b', value or '', re.I)
    return match[0] if match else None


def date_only(value):
    for pattern in ('%b %d, %Y', '%B %d, %Y %I:%M %p', '%B %d, %Y'):
        try:
            return datetime.strptime(value or '', pattern).date().isoformat()
        except ValueError:
            continue
    return None


def parse_usedcar(row, soup):
    product = next(json.loads(tag.string) for tag in soup.select('script[type="application/ld+json"]')
                   if tag.string and 'mileageFromOdometer' in tag.string)
    fields = {text(tag.find('th')): text(tag.find('td')) for tag in soup.select('table tr') if tag.find('th')}
    offer = product.get('offers', {})
    row.update(title=product['name'], brand=fields.get('Brand'), model=fields.get('Model'),
        used_inventory_basis='JSON-LD itemCondition=' + product.get('itemCondition', 'unknown'),
        model_year=numeric(fields.get('Manufacturing Year')), asking_price_npr=price(offer.get('price')),
        price_raw=offer.get('price'), odometer_km=numeric(fields.get('KM Driven')),
        engine_cc=numeric(fields.get('Engine Capacity')), fuel_type=fields.get('Fuel Type'),
        transmission=transmission(fields.get('Transmission')), drivetrain=drivetrain(fields.get('Wheel Drive')),
        condition_claim=fields.get('Condition'), body_type=fields.get('Body Type'), color=fields.get('Color'),
        location=fields.get('Location'), ownership_raw=fields.get('Ownership'),
        listing_status='live' if offer.get('availability', '').endswith('/InStock') else 'sold' if offer.get('availability', '').endswith(('/SoldOut', '/OutOfStock')) else 'unknown',
        image_urls=product.get('image', []), currency_basis='JSON-LD offers.priceCurrency', raw_fields=fields)
    if offer.get('priceCurrency') != 'NPR':
        row['asking_price_npr'] = None
        row['quality_flags'].append('unexpected_currency')
    whole = text(soup)
    listed = re.search(r'Listed:\s*([A-Za-z]+ \d{1,2}, \d{4})', whole)
    row['listing_date_raw'] = listed[1] if listed else None
    row['listing_date'] = date_only(row['listing_date_raw'])
    identifier = re.search(r'Car ID:\s*#(\d+)', whole)
    row['listing_id'] = identifier[1] if identifier else None
    economy = re.fullmatch(r'([\d.]+)\s*km/l', fields.get('Mileage', ''), re.I)
    row['fuel_economy_kmpl'] = float(economy[1]) if economy else None
    return product.get('description', '')


def parse_hamro(row, soup):
    title = text(soup.title).split(' | ')[0]
    heading = soup.find('h2', string=re.compile(r'^About This Car$'))
    values = [text(tag) for tag in heading.parent.select('.grp-1-subgrp p')]
    if len(values) != 6:
        raise ValueError('Unexpected Hamro specification layout: ' + repr(values))
    fields = dict(zip(('fuel', 'odometer', 'transmission_drivetrain', 'body', 'color', 'year'), values))
    price_tag = soup.find('h2', string=re.compile(r'^\s*Rs'))
    statuses = {'sold' if '/sold-car' in url else 'live' for url in row['discovered_from'] if not url.startswith('related_listing:') and re.search(r'/(?:sold-car|car)(?:\?|$)', url)}
    row.update(title=title, model_year=numeric(fields['year']), price_raw=text(price_tag),
        asking_price_npr=price(text(price_tag)), odometer_km=numeric(fields['odometer']), fuel_type=fields['fuel'],
        transmission=transmission(fields['transmission_drivetrain']), drivetrain=drivetrain(fields['transmission_drivetrain']),
        body_type=fields['body'], color=fields['color'], listing_id=row['source_url'].rstrip('/').split('/')[-1],
        listing_status=next(iter(statuses)) if len(statuses) == 1 else 'conflicting' if statuses else 'unknown',
        raw_fields=fields, image_urls=sorted({tag['src'] for tag in soup.select('img[src]') if '/uploads/car/' in tag['src']}))
    heading = soup.find('h2', string=re.compile(r'^Description$'))
    return text(heading.parent) if heading else ''


def parse_ktm(row, soup):
    fields = {}
    for tag in soup.select('li[id^="cp_"]'):
        if tag['id'] in ('cp_phone_no', 'cp_email_address'):
            continue
        label = text(tag.find('span'))
        fields[tag['id']] = text(tag).removeprefix(label).strip()
    title = text(soup.select_one('h1.single-listing'))
    if not title:
        raise ValueError('Missing KTM listing heading')
    description = text(soup.select_one('.single-main'))
    title_area = text(soup.select_one('h1.single-listing').parent)
    sold = bool(re.search(r'\bsold\b', title, re.I) or soup.select_one('.sold') or re.search(r'(?:this (?:item|ad|vehicle|car) (?:has been |is )?sold|marked as sold)', title_area, re.I))
    expires = fields.get('cp_expires', '')
    row.update(title=title, model_year=numeric(fields.get('cp_model_year')), price_raw=text(soup.select_one('.post-price')),
        asking_price_npr=price(text(soup.select_one('.post-price'))), odometer_km=numeric(fields.get('cp_odometer')),
        engine_cc=numeric(fields.get('cp_engine__cc')),
        fuel_type=fields.get('cp_fuel'), body_type=fields.get('cp_type'), color=fields.get('cp_color'),
        location=fields.get('cp_city'), ownership_raw=fields.get('cp_no_of_previous_owner'),
        listing_date_raw=fields.get('cp_listed'), listing_date=date_only(fields.get('cp_listed')),
        listing_status='sold' if sold else 'expired' if re.search(r'expired|ended', expires, re.I) else 'advertised_status_unconfirmed',
        raw_fields=fields, image_urls=sorted({tag['href'] for tag in soup.select('a[href]') if '/wp-content/uploads/' in tag['href'] and re.search(r'\.(?:jpg|jpeg|png)$', tag['href'], re.I)}))
    identifier = re.search(r'Listing ID:\s*([A-Za-z0-9]+)', text(soup))
    row['listing_id'] = identifier[1] if identifier else row['record_id']
    row['transmission'] = transmission(title)
    if not row['transmission']:
        match = re.search(r'(?:transmission|gearbox)\s*[:=-]?\s*(manual|automatic|auto|cvt|amt)|\b(manual|automatic|auto|cvt|amt)\s+(?:transmission|gearbox)', description, re.I)
        row['transmission'] = transmission(match[0]) if match else None
    row['drivetrain'] = drivetrain(title + ' ' + fields.get('cp_type', '') + ' ' + description)
    if fields.get('cp_condition'):
        row['used_inventory_basis'] = 'source cp_condition=' + fields['cp_condition']
        if fields['cp_condition'].lower() == 'new':
            row['vehicle_condition'] = 'conflicting_new_used_claims' if row['odometer_km'] else 'new_claimed'
            row['quality_flags'].append('source_new_category_conflicts_with_preowned_description_requires_review')
    return description


def parse_seecar(row, data):
    spec = (data.get('vehicle_specification') or {}).get('Specification_label_value') or {}
    flat = {key: value for section in spec.values() if isinstance(section, dict) for key, value in section.items()}
    fuel = data.get('engine_type')
    engine_value = next((value for key, value in flat.items() if re.search(r'(?:displacement|engine capacity)', key, re.I)), None)
    row.update(title=data['model'], brand=(data.get('manufacturer') or {}).get('name'),
        used_inventory_basis='public used filter and is_used=true',
        model_year=numeric(data.get('year')), price_raw=data.get('price'), asking_price_npr=price(data.get('price')),
        odometer_km=numeric(data.get('kilometers')), fuel_type='Electric' if fuel == 'EV' else fuel,
        transmission=transmission(data.get('transmission_type')), drivetrain=drivetrain(str(flat.get('Drive Type', ''))),
        engine_cc=numeric(engine_value), listing_id=str(data['id']),
        listing_status='sold' if data.get('sale_status') is True else 'live' if data.get('for_sale') else 'unknown',
        listing_date=data.get('created_at', '')[:10] or None, listing_date_raw=data.get('created_at'),
        updated_at_source=data.get('updated_at'), image_urls=json.loads(data.get('images') or '[]'),
        location=', '.join(filter(None, [data.get('address'), data.get('district_name')])),
        manufacturing_country_claim=data.get('country_of_origin'),
        raw_fields={key: data.get(key) for key in ('model', 'year', 'price', 'kilometers', 'mileage', 'engine_type', 'transmission_type', 'sale_status', 'for_sale', 'is_used', 'vehicle_color')})
    row['raw_fields']['specification_template_fields'] = {key: value for key, value in flat.items() if re.search(r'capacity|displacement|drive type|transmission type|fuel type', key, re.I)}
    row['raw_fields']['api_selling_price_unverified'] = data.get('selling_price')
    row['quality_flags'].append('specifications_include_model_template_not_vehicle_inspection')
    row['range_km' if fuel == 'EV' else 'fuel_economy_kmpl'] = numeric(data.get('mileage'))
    row['raw_fields']['mileage_semantics'] = 'claimed_range_km' if fuel == 'EV' else 'claimed_fuel_economy_kmpl'
    row['battery_capacity_kwh'] = numeric(flat.get('Battery Capacity(KWh)'))
    row['color'] = data.get('vehicle_color')
    return data.get('description') or ''


def review(row, description):
    row['title'] = redact(row['title'])
    row['description_excerpt'] = redact(description)[:750] or None
    row['brand'], row['model'], row['variant'] = match_identity(row['title'], row['brand'], row['model'])
    row['variant_candidate_raw'] = row['variant']
    row['variant_basis'] = 'unverified_title_suffix' if row['variant'] else None
    if row['variant'] and not re.search(r'\b(?:Magna|Sportz|Asta|Era|E\+?|EX|S|SX|SXO|HTE|HTK|HTX|GT|GTX|LX|GLS|GL|GLX|VXI|ZXI|ZDI|VDI|LXI|LDI|LUX|XZ|XM|XE|XZ\+|SMT|V|VX|SV|VMT|RXT|RXL|RXZ|RXE|RXS|Trend|Titanium|Highline|Comfortline|Trendline|Ambition|Elegance|Active|Base|Style|Superior|Advance|Premium|Allure|S11|S5|S4|Revo|Hi-Lander|HILANDER|Trail|S-AWC|Platinum|Limited|Sport|TX)\b', row['variant'], re.I):
        row['variant'] = None
        row['variant_basis'] = None
    row['condition_claim'] = row['condition_claim'] or condition(description)
    distance_claims = []
    patterns = [r'([\d,]+)\s*(?:km|kms|kilometers)\s*(?:driven|run)\b',
                r'\b(?:odometer|driven|run|only)\s*[:=-]?\s*([\d,]+)\s*(?:km|kms|kilometers)\b']
    for pattern in patterns:
        for match in re.finditer(pattern, description, re.I):
            prefix = re.split(r'[.;\n]', description[max(0, match.start() - 25):match.start()])[-1]
            suffix = re.split(r'[.;\n]', description[match.end():match.end() + 30])[0]
            context = prefix + match[0] + suffix
            if not re.search(r'range|warranty|charge|per liter|per litre', context, re.I):
                amount = numeric(match[1])
                if amount is not None:
                    distance_claims.append(amount)
    row['raw_fields']['description_odometer_claims_km'] = sorted(set(distance_claims))
    if row['odometer_km'] is None and len(set(distance_claims)) == 1:
        row['odometer_km'] = distance_claims[0]
        row['odometer_basis'] = 'explicit_seller_description_distance_claim'
    else:
        row['odometer_basis'] = 'source_structured_field' if row['odometer_km'] is not None else None
    if row['odometer_km'] is not None and any(amount != row['odometer_km'] for amount in distance_claims):
        row['quality_flags'].append('description_odometer_conflict')
    if row['engine_cc'] is None:
        engine = re.search(r'\b([\d,]+)\s*cc\b', description, re.I)
        row['engine_cc'] = numeric(engine[1]) if engine else None
    flags = row['quality_flags']
    years = set(int(value) for value in re.findall(r'\b(?:19|20)\d{2}\b', row['title']))
    if years and row['model_year'] not in years:
        flags.append('title_specification_year_conflict')
    if row['model_year'] is not None and not 1980 <= row['model_year'] <= 2026:
        flags.append('model_year_out_of_range_or_calendar_ambiguous')
    if row['asking_price_npr'] is None:
        flags.append('missing_or_malformed_price')
    elif not 100000 <= row['asking_price_npr'] <= 50000000:
        flags.append('price_outlier_requires_review')
    if row['odometer_km'] is not None and not 100 <= row['odometer_km'] <= 1000000:
        flags.append('odometer_zero_or_implausible_requires_review')
    if row['engine_cc'] is not None and not 600 <= row['engine_cc'] <= 6500:
        flags.append('engine_capacity_outlier')
    if row['fuel_type'] == 'Electric' and row['engine_cc']:
        flags.append('electric_vehicle_has_combustion_displacement')
    if row['model'] == 'Fortuner' and row['model_year'] and row['model_year'] <= 2015 and row['engine_cc'] and row['engine_cc'] < 2400:
        flags.append('older_fortuner_small_engine_claim_requires_source_verification')
    if row['model'] == 'Creta' and row['engine_cc'] and row['engine_cc'] < 1300:
        flags.append('creta_small_engine_claim_requires_source_verification')
    if row['listing_date']:
        age = (datetime.fromisoformat(row['captured_at_utc']).date() - datetime.fromisoformat(row['listing_date']).date()).days
        row['listing_age_days_at_capture'] = age
        if age > 180:
            flags.append('listing_older_than_180_days')
        elif age < 0:
            flags.append('listing_date_after_capture')
    else:
        row['listing_age_days_at_capture'] = None
    if row['model_year'] is not None:
        row['model_year'] = int(row['model_year'])
    if row['transmission'] == 'Manual' and re.search(r'\b(?:AMT|CVT|IVT|DCT|AT|automatic)\b', row['title'], re.I):
        flags.append('title_transmission_conflict')
    if row['fuel_type'] == 'Petrol' and re.search(r'\b(?:diesel|DSL)\b', row['title'], re.I):
        flags.append('title_fuel_conflict')
    if row['fuel_type'] != 'Electric' and re.search(r'\bEV\b', row['title'], re.I):
        flags.append('title_fuel_conflict')
    if row['listing_status'] in ('conflicting', 'unknown', 'advertised_status_unconfirmed'):
        flags.append('availability_not_confirmed')
    claims = []
    for match in re.finditer(r'(?:NPR|NRs|Rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?|\b(\d+(?:\.\d+)?)\s*(lakh|lac|crore)\b', description, re.I):
        amount = price(match[1] or match[3])
        unit = (match[2] or match[4] or '').lower()
        if amount is not None:
            claims.append(amount * (10000000 if unit == 'crore' else 100000 if unit in ('lakh', 'lac') else 1))
    row['raw_fields']['description_price_claims_npr'] = sorted(set(claims))
    if row['asking_price_npr'] is not None and any(abs(value - row['asking_price_npr']) > 1 for value in claims):
        flags.append('description_price_differs_requires_context_review')
    row['missing_fields'] = [key for key in ('brand', 'model', 'variant', 'model_year', 'asking_price_npr', 'odometer_km', 'transmission', 'drivetrain', 'condition_claim', 'listing_date') if row[key] is None]
    flags.extend('missing_' + key for key in row['missing_fields'])
    row['quality_flags'] = sorted(set(flags))
    return row


def deduplicate(rows, photo_hashes=None):
    unique = {}
    for row in rows:
        key = (row['source_site'], row['listing_id'] or row['source_url'])
        if key not in unique:
            unique[key] = row
        else:
            unique[key]['evidence'].extend(row['evidence'])
            unique[key]['discovered_from'] = sorted(set(unique[key]['discovered_from'] + row['discovered_from']))
    rows = list(unique.values())
    groups = defaultdict(list)
    for row in rows:
        if all(row[key] is not None for key in ('brand', 'model', 'model_year', 'odometer_km')):
            key = tuple(row[key] for key in ('brand', 'model', 'model_year', 'odometer_km'))
            groups[key].append(row)
    for key, members in groups.items():
        if len(members) > 1:
            group = hashlib.sha256(repr(key).encode()).hexdigest()[:14]
            for row in members:
                row['possible_duplicate_group'] = group
                row['quality_flags'].append('possible_same_vehicle_requires_review')
    if photo_hashes:
        removed = set()
        for members in groups.values():
            if len(members) < 2:
                continue
            members = sorted(members, key=lambda row: (row['listing_date'] or '', row['captured_at_utc']), reverse=True)
            for position, survivor in enumerate(members):
                if survivor['record_id'] in removed:
                    continue
                survivor_hashes = {photo_hashes[url]['sha256'] for url in survivor['image_urls'] if photo_hashes.get(url, {}).get('sha256')}
                matches = []
                for candidate in members[position + 1:]:
                    candidate_hashes = {photo_hashes[url]['sha256'] for url in candidate['image_urls'] if photo_hashes.get(url, {}).get('sha256')}
                    conflict = any(survivor[key] and candidate[key] and str(survivor[key]).lower() != str(candidate[key]).lower()
                                   for key in ('fuel_type', 'transmission', 'drivetrain', 'variant', 'color'))
                    if candidate['record_id'] not in removed and not conflict and len(survivor_hashes & candidate_hashes) >= 2:
                        matches.append(candidate)
                        removed.add(candidate['record_id'])
                if matches:
                    survivor['duplicate_observations'] = [dict(survivor)] + matches
                    survivor['duplicate_listing_urls'] = [entry['source_url'] for entry in survivor['duplicate_observations']]
                    survivor['deduplication_basis'] = 'same brand/model/year/odometer, compatible specifications and at least two byte-identical source photos'
                    survivor['quality_flags'].append('high_confidence_repost_consolidated_not_physically_verified')
                    if len({entry['asking_price_npr'] for entry in survivor['duplicate_observations']}) > 1:
                        survivor['quality_flags'].append('repost_advertised_price_changed_observations_retained')
                    if len({entry['listing_status'] for entry in survivor['duplicate_observations']}) > 1:
                        survivor['quality_flags'].append('repost_status_disagreement_observations_retained')
        rows = [row for row in rows if row['record_id'] not in removed]
    return sorted(rows, key=lambda row: (row['source_site'], row['source_url']))


def build():
    rows, errors, sources = [], [], []
    for host in HOSTS[:3]:
        folder = OUTPUT / host
        discovery = json.loads((folder / 'discovery.json').read_text(encoding='utf-8'))
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        for url, parents in discovery['discovered_listings'].items():
            try:
                evidence = manifest[url]
                data = (ROOT / evidence['snapshot_path']).read_bytes()
                if hashlib.sha256(data).hexdigest() != evidence['sha256']:
                    raise ValueError('Source checksum mismatch')
                soup = BeautifulSoup(data, 'html.parser', from_encoding='utf-8')
                row = empty_row(host, url, evidence, parents)
                description = {HOSTS[0]: parse_usedcar, HOSTS[1]: parse_ktm, HOSTS[2]: parse_hamro}[host](row, soup)
                rows.append(review(row, description))
                if len(rows) % 100 == 0:
                    print('Normalized', len(rows), 'listings', flush=True)
            except Exception as error:
                errors.append({'source_url': url, 'error': str(error)})
        sources.append({key: value for key, value in discovery.items() if key != 'discovered_listings'})
    manifest = json.loads((OUTPUT / 'admin.seecar.com/manifest.json').read_text())
    for key, evidence in manifest.items():
        if '/get/vehicle-by-id#' not in key:
            continue
        data = (ROOT / evidence['snapshot_path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != evidence['sha256']:
            raise ValueError('SeeCar checksum mismatch')
        item = json.loads(data)['data']
        if not item.get('is_used'):
            continue
        row = empty_row('seecar.com', 'https://seecar.com/car-detail/' + item['slug'], evidence, ['https://seecar.com/search-cars?is_used=true'])
        rows.append(review(row, parse_seecar(row, item)))
    sources.append(json.loads((OUTPUT / 'seecar.com/discovery.json').read_text()))
    captured_counts = dict(Counter(row['source_site'] for row in rows))
    hash_file = OUTPUT / 'duplicate-image-hashes.json'
    photo_hashes = json.loads(hash_file.read_text()) if hash_file.exists() else None
    rows = deduplicate(rows, photo_hashes)
    dataset = {'schema_version': '1.0', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Nepal used-car asking-price research; not approved training labels',
        'price_policy': 'Advertised prices only. SOLD and API selling_price do not establish actual transaction amounts. No price multipliers or imputation.',
        'missing_value_policy': 'null means unavailable or not safely parseable; see raw_fields and quality_flags',
        'deduplication_policy': 'Same source listing ID merged. Reposts with matching brand/model/year/odometer, compatible specs and two byte-identical photos consolidated with full observations. Other possible matches flagged, not deleted. Keep groups together in future splits.',
        'captured_advertisement_count': sum(captured_counts.values()), 'captured_counts_by_source': captured_counts,
        'consolidated_repost_count': sum(captured_counts.values()) - len(rows),
        'photo_hash_evidence_path': hash_file.relative_to(ROOT).as_posix() if photo_hashes else None,
        'privacy': 'No seller names, phones, emails, registration, engine or chassis numbers copied into normalized columns. Original public evidence snapshots remain local.',
        'source_coverage': sources, 'record_count': len(rows),
        'counts_by_source': dict(Counter(row['source_site'] for row in rows)),
        'counts_by_status': dict(Counter(row['listing_status'] for row in rows)),
        'parse_errors': errors, 'records': rows}
    target = ROOT / 'data/processed/nepal_used_cars_multisite.json'
    target.write_text(json.dumps(dataset, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({key: dataset[key] for key in ('record_count', 'counts_by_source', 'counts_by_status', 'parse_errors')}, indent=2))


if __name__ == '__main__':
    build()
