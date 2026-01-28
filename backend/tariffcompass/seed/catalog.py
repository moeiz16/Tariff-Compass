"""Northbound Goods Co.'s sample catalogue: about 120 products in five categories (docs/DATA.md).

Every product is sample data. Codes are real lines of the tariff editions the demo pins (HTSUS and Canada's
Customs Tariff); every ruling relied on is a real CBP ruling from the corpus (checked by the seed tests).
Values are typical shipments (customs value in USD, plus the Canadian value for duty in CAD).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Item:
    sku: str
    title: str
    category: str
    made_in: str
    us: str
    ca: str
    listing: str
    unit: Decimal  # unit value, USD
    qty: int
    transport: str = "ocean"
    into: tuple[str, ...] = ("US", "CA")
    material: str = ""
    rulings: tuple[str, ...] = ()
    family: str = ""
    deciding: tuple[str, str, str, str] | None = None  # (key, label, value, source note)
    extra: dict = field(default_factory=dict)

    @property
    def value(self) -> Decimal:
        return (self.unit * self.qty).quantize(Decimal("0.01"))

    @property
    def value_cad(self) -> Decimal:
        return (self.value * Decimal("1.37")).quantize(Decimal("0.01"))  # sample FX for the value for duty


D = Decimal

# Rulings relied on, by family (all in the corpus; see tests/test_seed.py)
R = {
    "vacuum": ("NY N321134", "HQ H303684"),
    "double_wall": ("NY N321985", "NY N297165"),
    "ss_cook": ("NY N265787",),
    "al_cook": ("NY N343672", "NY N341481"),
    "food": ("NY N342804", "NY N344429"),
    "knife": ("NY N333596",),
    "bike": ("NY N309424",),
    "torch": ("NY N331973", "NY N334131"),
    "power_bank": ("NY N350116", "NY N347094"),
    "speaker": ("NY N340388",),
    "speaker1": ("NY N341281",),
    "charger": ("NY N349433", "NY N343619"),
    "pullover": ("NY N329546",),
    "tee": ("NY N341977",),
    "base": ("NY N342008",),
    "fleece": ("NY N338957", "NY N344038"),
    "anorak": ("NY N337096",),
    "rain_w": ("NY N326613",),
    "sock": ("NY N329004",),
    "sock_syn": ("NY N322548",),
    "glove": ("NY N343677",),
    "tent": ("NY N304023", "NY N249601"),
    "tarp": ("NY N326879",),
    "sleeping": ("NY N266733",),
    "lantern": ("HQ H268599",),
    "stove": ("NY N341339",),
    "pole": ("NY N325073",),
    "backpack": ("NY N347592", "NY N343667"),
    "duffel": ("NY N335445",),
}


def _items() -> list[Item]:
    out: list[Item] = []

    def add(*args, **kw) -> None:
        out.append(Item(*args, **kw))

    # ── Kitchenware ──────────────────────────────────────────────────────────────────────────────────
    vac = (
        "Double-wall 18/8 stainless steel, vacuum insulated, powder-coated outside, BPA-free {lid}. Holds {ml} ml. "
        "Keeps drinks cold 24 h and hot 12 h."
    )
    for sku, oz, ml, lid, unit, qty in (
        ("NB-KT-0405", 12, 355, "slide lid", "6.80", 1500),
        ("NB-KT-0408", 16, 473, "screw lid with handle", "8.10", 1200),
        ("NB-KT-0412", 20, 591, "sliding lid", "12.50", 1000),
        ("NB-KT-0416", 26, 769, "straw lid", "13.20", 900),
        ("NB-KT-0420", 30, 887, "sliding lid and handle", "14.40", 800),
    ):
        listing = vac.format(lid=lid, ml=ml)
        if sku == "NB-KT-0412":
            listing = (
                "20 oz double-wall stainless steel tumbler, insulated, with a sliding lid. 18/8 stainless "
                "inside and out, powder-coated. Holds 591 ml."
            )
        add(
            sku,
            f"{oz} oz vacuum tumbler",
            "kitchen",
            "CN",
            "9617001000",
            "9617000000",
            listing,
            D(unit),
            qty,
            material="stainless steel",
            rulings=R["vacuum"],
            family="vacuum",
            deciding=("between_walls", "Between the walls", "A vacuum", "read from 'vacuum insulated'"),
        )
    add(
        "NB-KT-0424",
        "40 oz vacuum bottle",
        "kitchen",
        "CN",
        "9617003000",
        "9617000000",
        vac.format(lid="chug cap", ml=1183),
        D("16.90"),
        600,
        material="stainless steel",
        rulings=R["vacuum"],
        family="vacuum",
        deciding=("capacity", "Capacity", "1,183 ml", "your description"),
    )
    add(
        "NB-KT-0297",
        "64 oz insulated growler",
        "kitchen",
        "CN",
        "7323930080",
        "7323939090",
        "64 oz stainless steel growler, double wall with the air removed between the walls, swing-top cap. "
        "Holds 1.9 litres.",
        D("19.80"),
        500,
        material="stainless steel",
        rulings=("NY N297165",),
        family="double_wall",
        deciding=("between_walls", "Between the walls", "A vacuum", "your description"),
    )
    dw = "Double-wall stainless steel {what}, air-insulated (no vacuum), {lid}. Holds {ml} ml."
    for sku, title, what, lid, ml, unit in (
        ("NB-KT-0388", "20 oz double-wall camp tumbler", "tumbler", "sliding lid", 591, "7.40"),
        ("NB-KT-0391", "12 oz double-wall espresso cup", "cup", "no lid", 355, "4.20"),
        ("NB-KT-0394", "16 oz double-wall pint", "pint glass", "stackable rim", 473, "5.10"),
    ):
        add(
            sku,
            title,
            "kitchen",
            "CN",
            "7323930080",
            "7323939090",
            dw.format(what=what, lid=lid, ml=ml),
            D(unit),
            1200,
            material="stainless steel",
            rulings=R["double_wall"],
            family="double_wall",
            deciding=("between_walls", "Between the walls", "Air", "read from 'air-insulated'"),
        )
    for sku, title, made, unit, qty, detail in (
        (
            "NB-KT-0611",
            "Tri-ply stainless cookware set, 10 pieces",
            "DE",
            "142.00",
            220,
            "tri-ply 18/10 stainless steel with an aluminium core, induction-ready; 2 saucepans, sauté pan, stock pot, "
            "2 frying pans, 4 lids",
        ),
        ("NB-KT-0614", "Stainless saucepan, 2 L", "DE", "24.50", 600, "18/10 stainless steel, encapsulated base"),
        ("NB-KT-0617", "Stainless frying pan, 28 cm", "IT", "21.80", 700, "18/10 stainless steel, riveted handle"),
        ("NB-KT-0620", "Stainless stock pot, 8 L", "IT", "33.00", 400, "18/10 stainless steel, glass lid"),
        ("NB-KT-0623", "Camp cook pot, 1.2 L", "VN", "9.60", 1500, "stainless steel, folding handles, nests a stove"),
        ("NB-KT-0626", "Stainless mixing bowls, set of 3", "VN", "11.20", 900, "18/8 stainless steel, non-slip base"),
    ):
        add(
            sku,
            title,
            "kitchen",
            made,
            "7323930060",
            "7323939010",
            f"{title}: {detail}.",
            D(unit),
            qty,
            material="stainless steel",
            rulings=R["ss_cook"],
            family="ss_cook",
        )
    for sku, title, made, unit, qty, detail in (
        (
            "NB-KT-0645",
            "Hard-anodised aluminium frying pan, 26 cm",
            "IT",
            "18.40",
            800,
            "hard-anodised aluminium, three-layer non-stick, stay-cool handle",
        ),
        ("NB-KT-0648", "Aluminium camp pot set", "CN", "14.70", 1000, "anodised aluminium, 2 pots and a lid-pan"),
        ("NB-KT-0651", "Aluminium griddle, 2 burner", "CN", "22.30", 500, "pressed aluminium, non-stick"),
        ("NB-KT-0654", "Aluminium sauté pan with lid", "IT", "27.60", 400, "forged aluminium, induction disc"),
        ("NB-KT-0657", "Aluminium kettle, 1 L", "CN", "8.90", 900, "spun aluminium, for camp stoves"),
    ):
        add(
            sku,
            title,
            "kitchen",
            made,
            "7615107180",
            "7615100010",
            f"{title}: {detail}.",
            D(unit),
            qty,
            material="aluminium",
            rulings=R["al_cook"],
            family="al_cook",
        )
    for sku, title, made, unit, detail in (
        ("NB-KT-0702", "Food storage containers, set of 10", "CN", "9.80", "polypropylene, snap lids, freezer safe"),
        ("NB-KT-0705", "Stacking lunch box, 2 tier", "CN", "5.40", "polypropylene with a silicone seal"),
        ("NB-KT-0708", "Dry goods canisters, set of 4", "VN", "12.60", "clear plastic (SAN), airtight lids"),
        ("NB-KT-0711", "Collapsible camp bowls, set of 2", "CN", "4.10", "polypropylene rim, silicone sides"),
        ("NB-KT-0714", "Utensil set, nylon, 6 pieces", "VN", "6.30", "nylon heads, heat resistant to 210 °C"),
    ):
        add(
            sku,
            title,
            "kitchen",
            made,
            "3924104000",
            "3924100092",
            f"{title}: {detail}.",
            D(unit),
            2000,
            material="plastics",
            rulings=R["food"],
            family="food",
        )
    for sku, title, made, unit in (
        ("NB-KT-0731", "Chef's knife, 20 cm", "DE", "17.20"),
        ("NB-KT-0734", "Paring knife set, 3 pieces", "CN", "6.10"),
        ("NB-KT-0737", "Camp knife with sheath", "CN", "9.30"),
    ):
        add(
            sku,
            title,
            "kitchen",
            made,
            "8211929030",
            "8211920000",
            f"{title}: fixed blade of stainless steel, moulded handle.",
            D(unit),
            800,
            material="steel",
            rulings=R["knife"],
            family="knife",
        )

    # ── Small electronics ───────────────────────────────────────────────────────────────────────────
    for sku, title, unit, detail in (
        (
            "NB-EL-0215",
            "Rechargeable bicycle headlight, 800 lm",
            "14.00",
            "Rechargeable LED bicycle headlight, 800 lumens, USB-C. Mounts on the handlebar with a rubber strap; the "
            "lamp head detaches.",
        ),
        (
            "NB-EL-0218",
            "Bicycle headlight, 400 lm",
            "8.40",
            "LED bicycle headlight, 400 lumens, AAA batteries, fixed handlebar clamp.",
        ),
        (
            "NB-EL-0221",
            "Bicycle light set, front and rear",
            "11.60",
            "Bicycle light set: 300 lumen front light and red rear light, USB charging, silicone mounts.",
        ),
        (
            "NB-EL-0224",
            "Helmet-mount bike light",
            "12.90",
            "LED light for bicycle helmets, 500 lumens, rechargeable, helmet strap mount.",
        ),
    ):
        add(
            sku,
            title,
            "electronics",
            "CN",
            "8512102000",
            "8512100000",
            detail,
            D(unit),
            600,
            material="",
            rulings=R["bike"],
            family="bike",
            deciding=("torch_use", "Torch use", "Rides on the bike only", "your description"),
        )
    add(
        "NB-EL-0227",
        "Bicycle rear light, flashing",
        "electronics",
        "CN",
        "8512104000",
        "8512100000",
        "Red LED rear light for bicycles, flashing and steady modes, seat-post mount.",
        D("4.80"),
        1500,
        rulings=R["bike"],
        family="bike",
    )
    for sku, title, unit, detail in (
        ("NB-EL-0301", "Rechargeable headlamp, 450 lm", "9.70", "LED headlamp, 450 lumens, elastic head strap, USB-C"),
        ("NB-EL-0304", "Aluminium torch, 1,000 lm", "13.40", "LED flashlight, aluminium body, 18650 cell"),
        ("NB-EL-0307", "Mini keychain torch", "2.60", "LED flashlight, 100 lumens, button cells"),
        ("NB-EL-0310", "Waterproof dive torch", "18.20", "LED flashlight, 1,200 lumens, waterproof to 100 m"),
        ("NB-EL-0313", "Kids' headlamp", "5.20", "LED headlamp, 80 lumens, soft strap, AAA batteries"),
        ("NB-EL-0316", "Camp torch with lantern mode", "10.10", "LED flashlight with a diffuser cap, USB charging"),
    ):
        add(
            sku,
            title,
            "electronics",
            "CN",
            "8513102000",
            "8513101000",
            f"{detail}.",
            D(unit),
            1000,
            rulings=R["torch"],
            family="torch",
        )
    for sku, title, made, unit, mah in (
        ("NB-EL-0560", "Power bank, 10,000 mAh", "CN", "11.80", "10,000"),
        ("NB-EL-0563", "Power bank, 20,000 mAh", "CN", "18.60", "20,000"),
        ("NB-EL-0566", "Slim power bank, 5,000 mAh", "CN", "8.20", "5,000"),
        ("NB-EL-0569", "Solar power bank, 12,000 mAh", "CN", "16.40", "12,000"),
        ("NB-EL-0572", "Rugged power bank, 15,000 mAh", "VN", "17.10", "15,000"),
        ("NB-EL-0575", "MagSafe-style power bank, 5,000 mAh", "VN", "13.90", "5,000"),
    ):
        add(
            sku,
            title,
            "electronics",
            made,
            "8507600090",
            "8507609000",
            f"Portable power bank: lithium-ion cells, {mah} mAh, USB-C in/out and USB-A out.",
            D(unit),
            1200,
            material="lithium-ion cells",
            rulings=R["power_bank"],
            family="power_bank",
        )
    for sku, title, made, us, ca, fam, unit in (
        ("NB-EL-0401", "Bluetooth speaker, stereo", "MX", "8518220000", "8518220000", "speaker", "24.50"),
        ("NB-EL-0404", "Waterproof shower speaker", "CN", "8518210000", "8518210000", "speaker1", "9.80"),
        ("NB-EL-0407", "Party speaker with lights", "CN", "8518220000", "8518220000", "speaker", "38.00"),
        ("NB-EL-0410", "Bike-mount Bluetooth speaker", "VN", "8518210000", "8518210000", "speaker1", "14.60"),
        ("NB-EL-0413", "Camp speaker and lantern", "MX", "8518220000", "8518220000", "speaker", "29.90"),
    ):
        drivers = "two drivers in one enclosure" if us.endswith("220000") else "one driver"
        add(
            sku,
            title,
            "electronics",
            made,
            us,
            ca,
            f"Bluetooth 5.3 portable speaker, {drivers}, rechargeable battery, IPX5.",
            D(unit),
            800,
            rulings=R[fam],
            family=fam,
        )
    for sku, title, made, unit in (
        ("NB-EL-0451", "USB-C wall charger, 30 W", "CN", "5.90"),
        ("NB-EL-0454", "Dual USB wall charger, 20 W", "MX", "4.70"),
        ("NB-EL-0457", "GaN charger, 45 W", "VN", "9.40"),
        ("NB-EL-0460", "Travel charger with plugs", "CN", "8.80"),
        ("NB-EL-0463", "Car charger, 2 ports", "MX", "3.90"),
    ):
        add(
            sku,
            title,
            "electronics",
            made,
            "8504409510",
            "8504409041",
            f"{title}: static converter, AC to 5–20 V DC, output not exceeding 50 W.",
            D(unit),
            2000,
            rulings=R["charger"],
            family="charger",
        )

    # ── Apparel ─────────────────────────────────────────────────────────────────────────────────────
    for sku, title, made, us, ca, unit in (
        ("NB-AP-0102", "Women's crew-neck cotton pullover", "VN", "6110202020", "6110200092", "14.20"),
        ("NB-AP-0105", "Men's cotton fisherman sweater", "PT", "6110202010", "6110200091", "21.40"),
        ("NB-AP-0108", "Women's cotton cardigan", "VN", "6110202020", "6110200092", "16.80"),
        ("NB-AP-0111", "Men's cotton quarter-zip", "VN", "6110202010", "6110200091", "15.10"),
        ("NB-AP-0114", "Kids' cotton pullover", "VN", "6110202025", "6110200092", "8.90"),
        ("NB-AP-0118", "Women's brushed cotton pullover", "PT", "6110202020", "6110200012", "19.60"),
    ):
        knit = "brushed (fleeced) inside" if "brushed" in title else "ribbed cuffs and hem"
        add(
            sku,
            title,
            "apparel",
            made,
            us,
            ca,
            f"{title}: knitted, 100% cotton, {knit}.",
            D(unit),
            800,
            material="cotton",
            rulings=R["pullover"],
            family="pullover",
        )
    for sku, title, made, us, ca, fam in (
        ("NB-AP-0131", "Men's cotton T-shirt", "VN", "6109100012", "6109100012", "tee"),
        ("NB-AP-0134", "Women's cotton T-shirt", "MX", "6109100060", "6109100022", "tee"),
        ("NB-AP-0137", "Men's merino-blend base layer top", "CN", "6109901013", "6109900090", "base"),
        ("NB-AP-0140", "Women's polyester base layer top", "VN", "6109901065", "6109900010", "base"),
    ):
        add(
            sku,
            title,
            "apparel",
            made,
            us,
            ca,
            f"{title}: knitted jersey, crew neck, long sleeves.",
            D("7.60"),
            1500,
            material="cotton" if fam == "tee" else "polyester",
            rulings=R[fam],
            family=fam,
        )
    for sku, title, made in (
        ("NB-AP-0151", "Men's polar fleece jacket", "CN"),
        ("NB-AP-0154", "Men's grid fleece hoodie", "VN"),
        ("NB-AP-0157", "Men's sherpa fleece jacket", "CN"),
        ("NB-AP-0160", "Men's fleece vest", "VN"),
    ):
        add(
            sku,
            title,
            "apparel",
            made,
            "6101302010",
            "6101300000",
            f"{title}: knitted polyester fleece, full zip, two hand pockets.",
            D("17.30"),
            700,
            material="polyester",
            rulings=R["fleece"],
            family="fleece",
        )
    for sku, title, made, us, ca, fam in (
        ("NB-AP-0171", "Men's rain shell", "VN", "6201402015", "6201409011", "anorak"),
        ("NB-AP-0174", "Men's insulated anorak", "CN", "6201402015", "6201409019", "anorak"),
        ("NB-AP-0177", "Women's rain jacket", "VN", "6202402005", "6202400010", "rain_w"),
        ("NB-AP-0180", "Women's packable wind jacket", "CN", "6202402005", "6202400010", "rain_w"),
        ("NB-AP-0183", "Men's softshell jacket", "VN", "6201402015", "6201409019", "anorak"),
    ):
        add(
            sku,
            title,
            "apparel",
            made,
            us,
            ca,
            f"{title}: woven nylon shell, hood, taped seams.",
            D("26.40"),
            600,
            material="nylon",
            rulings=R[fam],
            family=fam,
        )
    for sku, title, made, us, ca, fam in (
        ("NB-AP-0201", "Cotton hiking socks, 3 pairs", "PT", "6115959000", "6115950020", "sock"),
        ("NB-AP-0204", "Cotton crew socks, 6 pairs", "CN", "6115959000", "6115950020", "sock"),
        ("NB-AP-0207", "Synthetic trail socks", "MX", "6115969020", "6115960030", "sock_syn"),
        ("NB-AP-0210", "Synthetic ski socks", "CN", "6115969020", "6115960030", "sock_syn"),
        ("NB-AP-0213", "Kids' cotton socks, 5 pairs", "PT", "6115959000", "6115950020", "sock"),
    ):
        add(
            sku,
            title,
            "apparel",
            made,
            us,
            ca,
            f"{title}: knitted, cushioned sole, no applied soles.",
            D("5.20"),
            2000,
            material="cotton" if fam == "sock" else "nylon",
            rulings=R[fam],
            family=fam,
        )
    for sku, title, made in (
        ("NB-AP-0231", "Knit touchscreen gloves", "CN"),
        ("NB-AP-0234", "Fleece-lined knit gloves", "VN"),
        ("NB-AP-0237", "Kids' knit mittens", "CN"),
        ("NB-AP-0240", "Liner gloves", "VN"),
    ):
        add(
            sku,
            title,
            "apparel",
            made,
            "6116938800",
            "6116930090",
            f"{title}: knitted of synthetic fibres, without fourchettes.",
            D("3.80"),
            2500,
            material="acrylic",
            rulings=R["glove"],
            family="glove",
        )

    # ── Outdoor gear ────────────────────────────────────────────────────────────────────────────────
    for sku, title, made, unit, qty in (
        ("NB-OD-0702", "Two-person backpacking tent", "CN", "62.00", 500),
        ("NB-OD-0705", "Ultralight one-person tent", "VN", "78.00", 300),
        ("NB-OD-0708", "Three-person backpacking tent", "CN", "71.00", 400),
        ("NB-OD-0711", "Four-season mountain tent", "VN", "118.00", 150),
        ("NB-OD-0714", "Bikepacking tent", "CN", "66.00", 300),
    ):
        add(
            sku,
            title,
            "outdoor",
            made,
            "6306221000",
            "6306220040",
            f"{title}: polyester fly and floor, aluminium poles, under 3 kg packed.",
            D(unit),
            qty,
            material="polyester",
            rulings=R["tent"],
            family="tent",
        )
    for sku, title in (
        ("NB-OD-0721", "Camp tarp, 3 x 3 m"),
        ("NB-OD-0724", "Ultralight tarp, 2 x 3 m"),
        ("NB-OD-0727", "Ground sheet, 2 x 2 m"),
    ):
        add(
            sku,
            title,
            "outdoor",
            "VN",
            "6306120000",
            "6306120000",
            f"{title}: coated polyester, grommets on every edge.",
            D("12.40"),
            900,
            material="polyester",
            rulings=R["tarp"],
            family="tarp",
        )
    for sku, title, made, us, unit in (
        ("NB-OD-0741", "Synthetic sleeping bag, -5 °C", "CN", "9404308000", "28.00"),
        ("NB-OD-0744", "Down sleeping bag, -10 °C", "VN", "9404304000", "64.00"),
        ("NB-OD-0747", "Summer sleeping bag, +10 °C", "CN", "9404308000", "15.20"),
        ("NB-OD-0750", "Kids' sleeping bag", "CN", "9404308000", "13.80"),
    ):
        fill = "duck down, 650 fill" if "Down" in title else "polyester fill"
        add(
            sku,
            title,
            "outdoor",
            made,
            us,
            "9404300000",
            f"{title}: nylon shell, {fill}, mummy cut.",
            D(unit),
            500,
            material="nylon",
            rulings=R["sleeping"],
            family="sleeping",
        )
    for sku, title, detail in (
        (
            "NB-OD-0731",
            "LED camp lantern with power bank",
            "LED camp lantern, 3 brightness levels, rechargeable 5,200 mAh battery with a USB-A output to charge a "
            "phone.",
        ),
        ("NB-OD-0734", "Collapsible LED lantern", "Collapsible LED camp lantern, AA batteries, hanging hook."),
        ("NB-OD-0737", "String lights for tents", "LED string lights, 5 m, USB powered, for tents and awnings."),
        ("NB-OD-0738", "Solar camp lantern", "LED lantern with a solar panel and inflatable diffuser."),
    ):
        add(
            sku,
            title,
            "outdoor",
            "CN",
            "9405428440",
            "9405429000",
            detail,
            D("10.90"),
            900,
            rulings=R["lantern"],
            family="lantern",
        )
    for sku, title in (
        ("NB-OD-0761", "Backpacking stove"),
        ("NB-OD-0764", "Two-burner camp stove"),
        ("NB-OD-0767", "Integrated stove and pot system"),
    ):
        add(
            sku,
            title,
            "outdoor",
            "CN",
            "7321111030",
            "7321119040",
            f"{title}: portable, for butane-propane canisters, steel and aluminium.",
            D("21.00"),
            600,
            material="steel",
            rulings=R["stove"],
            family="stove",
        )
    for sku, title in (
        ("NB-OD-0781", "Steel tent stakes, set of 10"),
        ("NB-OD-0784", "Snow stakes, set of 4"),
        ("NB-OD-0787", "Heavy-duty steel pegs, set of 8"),
    ):
        add(
            sku,
            title,
            "outdoor",
            "CN",
            "7326908688",
            "7326909090",
            f"{title}: forged steel, zinc plated.",
            D("3.10"),
            3000,
            material="steel",
            rulings=(),
            family="stake",
        )
    for sku, title in (
        ("NB-OD-0791", "Aluminium trekking poles, pair"),
        ("NB-OD-0794", "Carbon trekking poles, pair"),
        ("NB-OD-0797", "Folding trail poles, pair"),
    ):
        add(
            sku,
            title,
            "outdoor",
            "CN",
            "6602000000",
            "6602009000",
            f"{title}: adjustable walking sticks with cork grips and carbide tips.",
            D("14.50"),
            700,
            rulings=R["pole"],
            family="pole",
        )

    # ── Bags ────────────────────────────────────────────────────────────────────────────────────────
    for sku, title, made, unit in (
        ("NB-BG-0801", "Daypack, 22 L", "VN", "11.90"),
        ("NB-BG-0804", "Hiking backpack, 40 L", "VN", "24.60"),
        ("NB-BG-0807", "Commuter backpack with laptop sleeve", "CN", "17.80"),
        ("NB-BG-0810", "Kids' backpack", "CN", "6.40"),
        ("NB-BG-0813", "Hydration pack, 12 L", "VN", "13.70"),
    ):
        add(
            sku,
            title,
            "bags",
            made,
            "4202923120",
            "4202922090",
            f"{title}: outer surface of polyester textile, padded straps.",
            D(unit),
            900,
            material="polyester",
            rulings=R["backpack"],
            family="backpack",
        )
    for sku, title, made in (
        ("NB-BG-0821", "Travel duffel, 60 L", "VN"),
        ("NB-BG-0824", "Gear duffel, 90 L", "CN"),
        ("NB-BG-0827", "Packable duffel, 35 L", "VN"),
    ):
        add(
            sku,
            title,
            "bags",
            made,
            "4202923131",
            "4202929000",
            f"{title}: outer surface of nylon textile, shoulder strap.",
            D("15.20"),
            700,
            material="nylon",
            rulings=R["duffel"],
            family="duffel",
        )
    return out


PRODUCTS: list[Item] = _items()
BY_SKU: dict[str, Item] = {p.sku: p for p in PRODUCTS}


def all_ruling_ids() -> set[str]:
    ids = {r for rs in R.values() for r in rs}
    ids |= {r for p in PRODUCTS for r in p.rulings}
    return ids
