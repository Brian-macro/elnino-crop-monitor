from archive import content, observation
SOURCE = "cec"
URL = "https://www.sagis.org.za/wp-content/uploads/2026/08/CEC_2026-08-26.pdf"
def discover():
    return [{"url":URL,"publication_date":"2026-08-26","date_basis":"official CEC PDF date","title":"CEC seventh production forecast August 2026","suffix":".pdf"}]
def parse(doc):
    import io
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content(doc))).pages)
    for marker in ("18 096 865", "17 346 500", "3 010 175", "2 800 000"):
        if marker not in text: raise ValueError("CEC official table marker missing: " + marker)
    out = {"forecast": [], "estimate": []}
    for crop,current,prior,basis in [("corn",18.096865,17.3465,"grain"),("soybean",3.010175,2.8,"oilseed")]:
        out["forecast"].append(observation(doc,crop,"South Africa",2026,current,basis=basis,year_basis="calendar_year",methodology="CEC official seventh production forecast"))
        out["estimate"].append(observation(doc,crop,"South Africa",2025,prior,basis=basis,year_basis="calendar_year",methodology="CEC final prior crop in the same table"))
    return out
