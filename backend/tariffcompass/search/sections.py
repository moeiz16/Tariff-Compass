"""The 21 sections and 97 chapters of the Harmonized System (chapter 77 is reserved), for the classification path."""

from __future__ import annotations

SECTIONS: tuple[tuple[str, str, int, int], ...] = (
    ("I", "Live animals; animal products", 1, 5),
    ("II", "Vegetable products", 6, 14),
    ("III", "Animal, vegetable or microbial fats and oils", 15, 15),
    ("IV", "Prepared foodstuffs; beverages, spirits and vinegar; tobacco", 16, 24),
    ("V", "Mineral products", 25, 27),
    ("VI", "Products of the chemical or allied industries", 28, 38),
    ("VII", "Plastics and articles thereof; rubber and articles thereof", 39, 40),
    ("VIII", "Raw hides and skins, leather, furskins; saddlery; handbags and travel goods", 41, 43),
    ("IX", "Wood, cork and articles of plaiting materials", 44, 46),
    ("X", "Pulp of wood; paper and paperboard and articles thereof", 47, 49),
    ("XI", "Textiles and textile articles", 50, 63),
    ("XII", "Footwear, headgear, umbrellas, walking sticks", 64, 67),
    ("XIII", "Articles of stone, plaster, cement, ceramic products; glass", 68, 70),
    ("XIV", "Pearls, precious stones and metals; jewelry; coin", 71, 71),
    ("XV", "Base metals and articles of base metal", 72, 83),
    ("XVI", "Machinery and mechanical appliances; electrical equipment", 84, 85),
    ("XVII", "Vehicles, aircraft, vessels and associated transport equipment", 86, 89),
    ("XVIII", "Optical, photographic, measuring, medical instruments; clocks; musical instruments", 90, 92),
    ("XIX", "Arms and ammunition", 93, 93),
    ("XX", "Miscellaneous manufactured articles", 94, 96),
    ("XXI", "Works of art, collectors' pieces and antiques", 97, 97),
)

CHAPTERS: dict[str, str] = {
    "01": "Live animals", "02": "Meat and edible meat offal", "03": "Fish and crustaceans, molluscs",
    "04": "Dairy produce; birds' eggs; natural honey", "05": "Products of animal origin, not elsewhere specified",
    "06": "Live trees and other plants", "07": "Edible vegetables", "08": "Edible fruit and nuts",
    "09": "Coffee, tea, maté and spices", "10": "Cereals", "11": "Products of the milling industry",
    "12": "Oil seeds and oleaginous fruits", "13": "Lac; gums, resins and other vegetable saps",
    "14": "Vegetable plaiting materials", "15": "Animal, vegetable or microbial fats and oils",
    "16": "Preparations of meat, fish or crustaceans", "17": "Sugars and sugar confectionery",
    "18": "Cocoa and cocoa preparations", "19": "Preparations of cereals, flour, starch or milk",
    "20": "Preparations of vegetables, fruit or nuts", "21": "Miscellaneous edible preparations",
    "22": "Beverages, spirits and vinegar", "23": "Residues from the food industries; animal feed",
    "24": "Tobacco and manufactured tobacco substitutes", "25": "Salt; sulfur; earths and stone; lime and cement",
    "26": "Ores, slag and ash", "27": "Mineral fuels, mineral oils", "28": "Inorganic chemicals",
    "29": "Organic chemicals", "30": "Pharmaceutical products", "31": "Fertilizers",
    "32": "Tanning or dyeing extracts; paints and varnishes; inks", "33": "Essential oils; perfumery and cosmetics",
    "34": "Soap, washing preparations, waxes, candles", "35": "Albuminoidal substances; glues; enzymes",
    "36": "Explosives; matches", "37": "Photographic or cinematographic goods", "38": "Miscellaneous chemical products",
    "39": "Plastics and articles thereof", "40": "Rubber and articles thereof",
    "41": "Raw hides and skins and leather", "42": "Articles of leather; handbags and travel goods",
    "43": "Furskins and artificial fur", "44": "Wood and articles of wood", "45": "Cork and articles of cork",
    "46": "Manufactures of straw; basketware", "47": "Pulp of wood", "48": "Paper and paperboard",
    "49": "Printed books, newspapers, pictures", "50": "Silk", "51": "Wool, fine or coarse animal hair",
    "52": "Cotton", "53": "Other vegetable textile fibers", "54": "Man-made filaments", "55": "Man-made staple fibers",
    "56": "Wadding, felt and nonwovens; twine and rope", "57": "Carpets and other textile floor coverings",
    "58": "Special woven fabrics; lace; embroidery", "59": "Impregnated, coated or laminated textile fabrics",
    "60": "Knitted or crocheted fabrics", "61": "Apparel and clothing accessories, knitted or crocheted",
    "62": "Apparel and clothing accessories, not knitted or crocheted", "63": "Other made-up textile articles",
    "64": "Footwear, gaiters and the like", "65": "Headgear and parts thereof",
    "66": "Umbrellas, walking sticks, whips", "67": "Prepared feathers; artificial flowers",
    "68": "Articles of stone, plaster, cement, asbestos, mica", "69": "Ceramic products", "70": "Glass and glassware",
    "71": "Pearls, precious stones, precious metals; jewelry; coin", "72": "Iron and steel",
    "73": "Articles of iron or steel", "74": "Copper and articles thereof", "75": "Nickel and articles thereof",
    "76": "Aluminum and articles thereof", "77": "(Reserved)", "78": "Lead and articles thereof",
    "79": "Zinc and articles thereof", "80": "Tin and articles thereof", "81": "Other base metals; cermets",
    "82": "Tools, implements, cutlery, spoons and forks, of base metal",
    "83": "Miscellaneous articles of base metal",
    "84": "Nuclear reactors, boilers, machinery and mechanical appliances",
    "85": "Electrical machinery and equipment; sound and television equipment",
    "86": "Railway or tramway locomotives and rolling stock", "87": "Vehicles other than railway or tramway",
    "88": "Aircraft, spacecraft", "89": "Ships, boats and floating structures",
    "90": "Optical, photographic, measuring, medical or surgical instruments", "91": "Clocks and watches",
    "92": "Musical instruments", "93": "Arms and ammunition",
    "94": "Furniture; bedding, mattresses, cushions; lamps and lighting fittings; prefabricated buildings",
    "95": "Toys, games and sports equipment", "96": "Miscellaneous manufactured articles",
    "97": "Works of art, collectors' pieces and antiques",
}  # fmt: skip


def section_of(chapter: str) -> tuple[str, str]:
    n = int(chapter[:2])
    for roman, title, lo, hi in SECTIONS:
        if lo <= n <= hi:
            return roman, title
    return "", ""


def chapter_title(chapter: str) -> str:
    return CHAPTERS.get(chapter[:2], "")
