/** The 97 chapters of the Harmonized System in their 21 sections (chapter 77 is held in reserve). */
import type { SectionOut } from "../types";

const S: [string, string, [number, number]][] = [
  ["I", "Live animals; animal products", [1, 5]],
  ["II", "Vegetable products", [6, 14]],
  ["III", "Animal, vegetable or microbial fats and oils", [15, 15]],
  ["IV", "Prepared foodstuffs; beverages, spirits and vinegar; tobacco", [16, 24]],
  ["V", "Mineral products", [25, 27]],
  ["VI", "Products of the chemical or allied industries", [28, 38]],
  ["VII", "Plastics and rubber, and articles thereof", [39, 40]],
  ["VIII", "Hides, skins, leather and travel goods", [41, 43]],
  ["IX", "Wood, cork and basketware", [44, 46]],
  ["X", "Pulp, paper and printed matter", [47, 49]],
  ["XI", "Textiles and textile articles", [50, 63]],
  ["XII", "Footwear, headgear, umbrellas", [64, 67]],
  ["XIII", "Articles of stone, ceramic and glass", [68, 70]],
  ["XIV", "Pearls, precious stones and metals", [71, 71]],
  ["XV", "Base metals and articles of base metal", [72, 83]],
  ["XVI", "Machinery and electrical equipment", [84, 85]],
  ["XVII", "Vehicles, aircraft, vessels", [86, 89]],
  ["XVIII", "Optical, medical and measuring instruments; clocks; musical instruments", [90, 92]],
  ["XIX", "Arms and ammunition", [93, 93]],
  ["XX", "Miscellaneous manufactured articles", [94, 96]],
  ["XXI", "Works of art, collectors' pieces and antiques", [97, 97]],
];

const T: Record<number, string> = {
  1: "Live animals", 2: "Meat", 3: "Fish and seafood", 4: "Dairy, eggs, honey", 5: "Other animal products",
  6: "Live plants and flowers", 7: "Vegetables", 8: "Fruit and nuts", 9: "Coffee, tea and spices", 10: "Cereals",
  11: "Milling products", 12: "Oil seeds", 13: "Lacs, gums, resins", 14: "Vegetable plaiting materials",
  15: "Fats and oils", 16: "Preparations of meat or fish", 17: "Sugars", 18: "Cocoa", 19: "Cereal preparations",
  20: "Vegetable and fruit preparations", 21: "Miscellaneous food preparations", 22: "Beverages", 23: "Food residues and animal feed",
  24: "Tobacco", 25: "Salt, stone, cement", 26: "Ores", 27: "Mineral fuels", 28: "Inorganic chemicals", 29: "Organic chemicals",
  30: "Pharmaceutical products", 31: "Fertilisers", 32: "Dyes, paints, inks", 33: "Essential oils and cosmetics", 34: "Soaps and waxes",
  35: "Proteins and glues", 36: "Explosives and matches", 37: "Photographic goods", 38: "Miscellaneous chemical products",
  39: "Plastics", 40: "Rubber", 41: "Hides and leather", 42: "Leather goods and travel bags", 43: "Furskins", 44: "Wood",
  45: "Cork", 46: "Basketware", 47: "Wood pulp", 48: "Paper and paperboard", 49: "Printed books", 50: "Silk", 51: "Wool",
  52: "Cotton", 53: "Other vegetable fibres", 54: "Man-made filaments", 55: "Man-made staple fibres", 56: "Wadding, felt, cordage",
  57: "Carpets", 58: "Special woven fabrics", 59: "Coated textile fabrics", 60: "Knitted fabrics", 61: "Apparel, knitted",
  62: "Apparel, not knitted", 63: "Other made-up textile articles", 64: "Footwear", 65: "Headgear", 66: "Umbrellas and walking sticks",
  67: "Feathers and artificial flowers", 68: "Articles of stone", 69: "Ceramic products", 70: "Glass", 71: "Pearls and precious metals",
  72: "Iron and steel", 73: "Articles of iron or steel", 74: "Copper", 75: "Nickel", 76: "Aluminium", 77: "(Reserved)", 78: "Lead",
  79: "Zinc", 80: "Tin", 81: "Other base metals", 82: "Tools and cutlery", 83: "Miscellaneous articles of base metal",
  84: "Machinery", 85: "Electrical equipment", 86: "Railway equipment", 87: "Vehicles", 88: "Aircraft", 89: "Ships and boats",
  90: "Optical and medical instruments", 91: "Clocks and watches", 92: "Musical instruments", 93: "Arms and ammunition",
  94: "Furniture, bedding, lamps", 95: "Toys, games, sports equipment", 96: "Miscellaneous manufactured articles", 97: "Works of art",
};

export const SECTIONS: SectionOut[] = S.map(([section, title, [a, b]]) => ({
  section,
  title,
  chapters: Array.from({ length: b - a + 1 }, (_, i) => {
    const n = a + i;
    return { chapter: String(n).padStart(2, "0"), title: T[n] ?? "", reserved: n === 77 };
  }),
}));
