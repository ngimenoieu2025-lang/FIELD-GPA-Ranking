"""Reproducible, reviewable broad-area crosswalk for the US replication.

The source workbook supplies institution-specific department names and areas.
Name rules refine these broad areas; they do not claim a 29-field equivalence.
"""
import re
import pandas as pd

SPANISH_AREAS = {
    'Education': ['Early childhood teaching', 'Primary teaching', 'Other education'],
    'Arts, media & architecture': ['Arts', 'Audiovisual & media', 'Architecture'],
    'Humanities & languages': ['Humanities', 'Languages'],
    'Social sciences & law': ['Psychology', 'Economics', 'Other social sciences', 'Journalism', 'Law', 'Social work'],
    'Business': ['Business administration', 'Other business'],
    'Science, mathematics & computing': ['Life sciences', 'Physical sciences', 'Mathematics & statistics', 'Computer science'],
    'Engineering': ['Engineering'],
    'Agriculture': ['Agriculture'],
    'Health & veterinary': ['Medicine', 'Nursing', 'Other health', 'Veterinary'],
    'Sports, tourism & services': ['Sports', 'Tourism', 'Other services'],
}
SPANISH_TO_AREA = {f: a for a, fields in SPANISH_AREAS.items() for f in fields}
SOURCE_AREAS = {
    'Art, Media, and Architecture': 'Arts, media & architecture',
    'Foreign Language': 'Humanities & languages', 'Humanities': 'Humanities & languages',
    'Social Sciences': 'Social sciences & law', 'Business': 'Business',
    'Engineering': 'Engineering', 'Health and Medicine': 'Health & veterinary',
    'Non-engineering Sciences and Mathematics': 'Science, mathematics & computing',
}
# Ordered rules: professional health and subject-teacher training precede
# generic sports/agriculture/engineering words in department names.
RULES = [
    ('Health & veterinary', r'nurs|veterinar|pharmac|dent(al|ist)|medical|medicine|public health|epidemi|health education|health promotion|community health|physical therapy|occupational therapy|athletic training|audiolog|speech.*(hearing|patholog)|radiolog|nutrition|dietet|psychiatr|clinical|rehabilitation|health science|health service|health polic|health care|healthcare|allied health'),
    ('Sports, tourism & services', r'physical\s+education'),
    ('Education', r'\beduc|\bedc\b|\bed leadership|\bed policy|\bed\.?$|teacher|teaching|curricul|pedagog|instruction|learning sciences|learning disabil|school leadership|exceptional children|literacy|\breading\b|language arts'),
    ('Sports, tourism & services', r'sport|kinesiolog|exercise|recreation|tourism|hospitality|hotel|restaurant|physical education|athletics|movement science|fitness|leisure'),
    ('Engineering', r'engineer|\bengr\b'),
    ('Agriculture', r'agricultur|agribusiness|agriculut|agronom|horticultur|crop|soil|forestr|forest |fish(er|ery)|wildlife|animal science|animal production|animal nutrition|poultry|dairy|equine|plant science|plant pathology|viticultur|enology'),
    ('Social sciences & law', r'psycholog|econom|sociolog|anthropolog|politic|crimin|criminal justice|legal|\blaw\b|social work|social welfare|public admin|public affairs|public policy|journalis|communication|library|librar|counseling'),
    ('Arts, media & architecture', r'architect|urban.*planning|city.*planning|regional planning|environmental design|\bart\b|\barts\b|music|theatr|drama|dance|cinema|film|media'),
]

def normalize(value):
    return re.sub(r'\s+', ' ', str(value or '').strip())


def classify(name, source):
    """Return broad area and reason, leaving genuinely unclear names excluded."""
    n = normalize(name).lower()
    if not n or n in {'nan', 'na', 'none'}:
        return '', 'excluded: missing department name'
    if re.search(r'general education|core curriculum|college park scholars|study abroad|^gen ed$|^honors$|^seminar|^cooperative education$', n):
        return '', 'excluded: general programme'
    if source in {'Uncategorized', 'Interdisciplinary and Individualized Study',
                  'Honors, Leadership, General Education and Academic Support Seminars', 'Military and ROTC'}:
        return '', 'excluded: ambiguous or non-comparable source area'
    for area, pattern in RULES:
        if re.search(pattern, n):
            return area, 'department-name rule'
    if source in SOURCE_AREAS:
        return SOURCE_AREAS[source], 'source-area fallback'
    # The public-service bucket mixes education, library science, social work,
    # law, and generic courses; only explicit name rules above are retained.
    return '', 'excluded: no defensible broad-area match'


def build_mapping(raw):
    book = pd.read_excel(raw / 'dept_name_code_field_mapping.xlsx', sheet_name=None, dtype=str, keep_default_na=False)
    rows = []
    for csv in sorted(raw.rglob('*.csv')):
        sheet = csv.name[:31]
        if sheet not in book:
            raise ValueError(f'No workbook sheet for {csv.name}: expected {sheet}')
        for _, r in book[sheet].iterrows():
            area, rule = classify(r['Department_Name'], r['Field'])
            rows.append({'univ': csv.stem, 'department_code': normalize(r['Department_Code']),
                         'department_name': normalize(r['Department_Name']), 'source_area': r['Field'],
                         'field': area, 'mapping_rule': rule})
    out = pd.DataFrame(rows)
    if out.duplicated(['univ', 'department_code']).any():
        raise ValueError('Duplicate university/department keys in source mapping')
    return out
